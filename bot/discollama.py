import io
import os
import json
import asyncio
import argparse
from datetime import datetime, timedelta

import ollama
import discord
import redis
import random

from logging import getLogger

# piggy back on the logger discord.py set up
logging = getLogger('discord.bot')
chat_max_length = 500
admin_id = ""
ready = False

class DiscordResponse:
  def __init__(self, message):
    self.message = message
    self.channel = message.channel

    self.r = None
    self.sb = io.StringIO()

  async def write(self, message, s, end=''):
    if self.sb.seek(0, io.SEEK_END) + len(s) + len(end) > 2000:
      self.r = None
      self.sb.seek(0, io.SEEK_SET)
      self.sb.truncate()

    self.sb.write(s)

    value = self.sb.getvalue().strip()
    if not value:
      logging.info('Empty response, not sending')
      value = '*I don\'t have anything to say.*'

    self.r = await self.channel.send(value, reference=message)


class Bot:
  def __init__(self, ollama, discord, redis, model, admin_id, prompt):
    self.ollama = ollama
    self.discord = discord
    self.redis = redis
    self.model = model
    self.admin_id = admin_id
    self.prompt = prompt
    self.ready = False

    # register event handlers
    self.discord.event(self.on_ready)
    self.discord.event(self.on_message)

  async def on_ready(self):    
    # pull the model
    await self.ollama.pull(self.model)
    
    activity = discord.Activity(name='Status', state='Hi, I\'m mike! I only respond to mentions.', type=discord.ActivityType.custom)
    await self.discord.change_presence(activity=activity)

    logging.info(
      'Ready! Invite URL: %s',
      discord.utils.oauth_url(
        self.discord.application_id,
        permissions=discord.Permissions(
          read_messages=True,
          send_messages=True,
          create_public_threads=True,
        ),
        scopes=['bot'],
      ),
    )
    
    self.ready = True

  def message(self, message, content=''):
    return f'**at {message.created_at.strftime("%Y-%m-%d %H:%M:%S")} {message.author.name}({message.author.id}) said in {message.channel.name}**: {content}'

  async def on_message(self, message):
    if not self.ready:
      return
    
    string_channel_id = str(message.channel.id)
    
    if self.discord.user == message.author:
      # don't respond to ourselves
      return

    if not self.discord.user.mentioned_in(message) or message.author.bot or '@everyone' in message.content or '@here' in message.content:
      # don't respond to messages that don't mention us, but save it for context
      await self.save_message(str(message.channel.id), self.message(message, message.content), 'user')
      logging.info('Message saved for context in guild %s, but it was not for us', message.channel.guild.name)
      
      # However, if randomly it does accept the message, and respond. There is a 0.01% chance of it happening.
      if random.random() > 0.0001:
        return

    content = message.content.replace(f'<@{self.discord.user.id}>', 'Mike').strip()
    if not content:
      return
      
    if content == 'RESET' and str(message.author.id) == self.admin_id:
      await self.flush_channel(str(message.channel.id))
      logging.info('Chat reset by admin in guild %s', message.channel.guild.name)
      await self.save_message(string_channel_id, '*You joined the chat! - You joined ' + str(message.channel.guild.name) + '.*', 'assistant')
      return
    elif content == 'RESET' and str(message.author.id) != self.admin_id:
      logging.info('Chat reset denied by user %s in guild %s', message.author.name, message.channel.guild.name)
      content = message.author.name + ' tried to reset the chat, but was denied.'

    channel = message.channel

    logging.info('Generating response for message %s in channel %s', message.id, channel.id)
    
    # Create response
    r = DiscordResponse(message)
    # if r.channel.type == discord.ChannelType.text:
    #   await r.write('**Starting chat...**\n')
    
    task = asyncio.create_task(self.thinking(message))
    
    # Save user message
    await self.save_message(string_channel_id, self.message(message, content), 'user')
    
    # Generate text for response
    response = await self.chat(string_channel_id)

    # Write response
    # Truncate response if too long
    await r.write(message, response[:2000])
    task.cancel()
    

  async def thinking(self, message, timeout=999):
    try:
      # await message.add_reaction('🤔')
      async with message.channel.typing():
        await asyncio.sleep(timeout)
    except Exception:
      pass

  async def chat(self, channel_id):
    try:
      local_messages = await self.load_channel(channel_id)
      local_messages.append({'role': 'system', 'content': self.prompt})
      
      response_message = ''
      data = await self.ollama.chat(model=self.model, keep_alive=-1, stream=False, messages=local_messages)
      
      response_message = data['message']['content']
      await self.save_message(channel_id, response_message, 'assistant')      
        
      return response_message
    except Exception as e:
      logging.error('Error generating response: %s', e)
      return 'I am sorry, I am unable to respond at the moment.'
  
  async def load_channel(self, channel_id):
    ctx = self.redis.get(f'discollama:channel:{channel_id}')
    return json.loads(ctx) if ctx else []
  
  async def flush_channel(self, channel_id):
    self.redis.delete(f'discollama:channel:{channel_id}')
  
  async def save_message(self, channel_id, message, role):
    if message.strip() == '':
      return
    
    # Generate message structure
    content = {
      'role': role,
      'content': message
    }
    logging.info('for channel %s, saving message %s', channel_id, content)
    
    # Load messages
    messages = await self.load_channel(channel_id)
    
    # If above max chat entries, remove the oldest
    if len(messages) > chat_max_length:
      messages.pop(0)
    
    # Append new message
    messages.append(content)
    
    # Convert to string
    messages = json.dumps(messages)
    
    # Save messages
    self.redis.set(f'discollama:channel:{channel_id}', messages, ex=60 * 60 * 24 * 7)

  def run(self, token):
    logging.info('Starting bot...')
    try:
      self.discord.run(token)
    except Exception:
      self.redis.close()

def main():
  parser = argparse.ArgumentParser()

  parser.add_argument('--ollama-scheme', default=os.getenv('OLLAMA_SCHEME', 'http'), choices=['http', 'https'])
  parser.add_argument('--ollama-host', default=os.getenv('OLLAMA_HOST', '127.0.0.1'), type=str)
  parser.add_argument('--ollama-port', default=os.getenv('OLLAMA_PORT', 11434), type=int)
  parser.add_argument('--ollama-model', default=os.getenv('OLLAMA_MODEL', 'llama3'), type=str)

  parser.add_argument('--redis-host', default=os.getenv('REDIS_HOST', '127.0.0.1'), type=str)
  parser.add_argument('--redis-port', default=os.getenv('REDIS_PORT', 6379), type=int)
  
  parser.add_argument('--admin-id', default=os.getenv('ADMIN_ID', ''), type=str)
  
  parser.add_argument('--prompt', default='Hi, I\'m mike! An AI chatbot on Discord.', type=str)

  parser.add_argument('--buffer-size', default=32, type=int)

  args = parser.parse_args()

  intents = discord.Intents.default()
  intents.message_content = True

  Bot(
    ollama.AsyncClient(host=f'{args.ollama_scheme}://{args.ollama_host}:{args.ollama_port}'),
    discord.Client(intents=intents),
    redis.Redis(host=args.redis_host, port=args.redis_port, db=0, decode_responses=True),
    model=args.ollama_model,
    admin_id = args.admin_id,
    prompt=args.prompt
  ).run(os.environ['DISCORD_TOKEN'])


if __name__ == '__main__':
  main()
