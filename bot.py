# Build in imports
import io
import os
import json
import asyncio
import argparse
from logging import getLogger
import random

# External imports
import ollama
import discord
import redis

# piggy back on the logger discord.py set up
logging = getLogger('discord.bot')

class DiscordResponse:
  def __init__(self, message):
    self.message = message
    self.channel = message.channel

    self.r = None

  async def write(self, message, s, end=''):

    value = self.sanitize(s)
    if not value:
      logging.info('Empty response, not sending')
      value = '*I don\'t have anything to say.*'

    # Reply with multiple messages if the response is too long. The first one should reference the original message.
    i = 0
    if len(value) >= 2000:
      done = False
      referenced = False
      message_remaining = value

      while not done:
        i += 1
        if i > 10:
          logging.info('Too many chunks, stopping')
          break
        
        # Find the last newline before the 2000 character limit
        split_index = message_remaining.rfind('\n', 0, 2000)

        # If there's no newline, just split at the 2000 character limit
        if split_index == -1:
            split_index = 2000
            logging.info('Splitting at 2000 characters - no newline found')
            
            if len(message_remaining) <= 2000:
              split_index = len(message_remaining)
            
        # Get the chunk to send
        logging.info('Sending chunk of length %s, of %s', len(message_remaining[:split_index]), len(message_remaining))
        chunk_to_send = message_remaining[:split_index]

        if len(chunk_to_send) == 0 and len(message_remaining) > 0 and len(message_remaining) <= 2000:
          chunk_to_send = message_remaining
          done = True
        if len(chunk_to_send) == 0:
          done = True
          logging.info('Empty chunk, stopping')
          continue
        
        # Send the chunk here
        if not referenced:
          self.r = await self.channel.send(chunk_to_send, reference=message)
          referenced = True
        else:
          await self.channel.send(chunk_to_send)

        # Update the remaining message
        message_remaining = message_remaining[split_index:]

        # If there's nothing left to send, we're done
        if len(message_remaining) == 0:
            done = True
            logging.info('No more message to send')
            break
            
        # Wait a bit to avoid rate limiting
        await asyncio.sleep(0.5)
        
    else:
        await self.channel.send(value, reference=message)
    
  def sanitize(self, message):
    stripped = message.strip()
    non_mentioned = stripped.replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere')
    escaped = discord.utils.escape_mentions(non_mentioned)
    
    return escaped


class Bot:
  def __init__(self, ollama, discord, redis, model, admin_id, chat_channel_id, bot_name, chat_max_length=500, ctx=4096):
    self.ollama = ollama
    self.discord = discord
    self.redis = redis
    self.model = model
    self.admin_id = admin_id
    self.chat_channel_id = chat_channel_id
    self.bot_name = bot_name
    self.chat_max_length = chat_max_length
    self.ctx = ctx
    self.ready = False

    # register event handlers
    self.discord.event(self.on_ready)
    self.discord.event(self.on_message)

  async def on_ready(self):    
    # pull the model
    # await self.ollama.pull(self.model)
    
    activity = discord.Activity(name='Status', state=f'Hi, I\'m {self.bot_name.title()}! I only respond to mentions.', type=discord.ActivityType.custom)
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
    try:
      said = "said"
      if message.reference:
        said = f'replied to {message.reference.message_id}'
        
      chat_name = "this chat"
      try:
        chat_name = message.channel.name
      except Exception as e:
        pass
      
      return f'**({message.id}) at {message.created_at.strftime("%Y-%m-%d %H:%M:%S")} {message.author.name}({message.author.id}) {said} in {chat_name}**: {content}'
    except Exception as e:
      logging.error('Error generating message: %s', e)
      return ''

  async def on_message(self, message):
    if not self.ready:
      return
        
    string_channel_id = str(message.channel.id)
    
    # If CHAT_CHANNEL_ID is set, only respond in that channel.
    if self.chat_channel_id:
      if string_channel_id != self.chat_channel_id:
        return
    
    if self.discord.user == message.author:
      # don't respond to ourselves
      return
    
    # Do not respond with llm in private messages
    if isinstance(message.channel, discord.DMChannel):
      response = DiscordResponse(message)
      if self.discord.user.mentioned_in(message):
        await response.write(message, 'I am sorry, I am unable to respond in private messages.')
      return

    # Do not respond to messages that don't mention us
    if not self.discord.user.mentioned_in(message) or message.author.bot or '@everyone' in message.content or '@here' in message.content:
      # don't respond to messages that don't mention us, but save it for context
      await self.save_message(str(message.channel.id), self.message(message, message.content), 'user')
      logging.info('Message saved for context in %s, but it was not for us', (message.channel.id))
      
      # However, if randomly it does accept the message, and respond. There is a 0.01% chance of it happening.
      if (random.random() * 1000) > 0.1:
        return

    # Clean message
    content = message.content.replace(f'<@{self.discord.user.id}>', self.bot_name.title()).strip()
    if not content:
      return
    
    # Admin commands
    if content == 'RESET' and str(message.author.id) == self.admin_id:
      await self.flush_channel(str(message.channel.id))
      logging.info('Chat reset by admin in %s', (message.channel.id))
      await self.save_message(string_channel_id, '*You joined the chat! - You joined ' + str(message.channel.guild.name) + '.*', 'assistant')
      return
    elif content == 'RESET' and str(message.author.id) != self.admin_id:
      logging.info('Chat reset denied by user %s in %s', message.author.name, (message.channel.id))
      content = message.author.name + ' tried to reset the chat, but was denied.'

    channel = message.channel

    logging.info('Generating response for message %s in channel %s', message.id, channel.id)
    
    # Create response
    r = DiscordResponse(message)
    
    task = asyncio.create_task(self.thinking(message))
    
    try:
      # Save user message
      await self.save_message(string_channel_id, self.message(message, content), 'user')
      
      # Generate text for response
      response = await self.chat(string_channel_id)

      # Write response
      # Truncate response if too long
      await r.write(message, response)
      await asyncio.sleep(0.5)
    except Exception as e:
      logging.error('Error sending response: %s', e)
    finally:
      task.cancel()
    

  async def thinking(self, message, timeout=999):
    try:
      async with message.channel.typing():
        await asyncio.sleep(timeout)
    except Exception:
      pass

  async def chat(self, channel_id):
    try:
      local_messages = await self.load_channel(channel_id)
      
      response_message = ''
      data = await self.ollama.chat(model=self.model, keep_alive=-1, stream=False, messages=local_messages, options={'num_ctx': self.ctx})
      
      try:
        response_message = data['message']['content']
        await self.save_message(channel_id, response_message, 'assistant')      
      except Exception as e:
        logging.error('Error saving response: %s', e)
        return 'I am sorry, I am unable to respond at the moment.'
        
      return response_message
    except Exception as e:
      logging.error('Error generating response: %s', e)
      return 'I am sorry, I am unable to respond at the moment.'
  
  async def load_channel(self, channel_id):
    redis_content = self.redis.get(f'discollama:channel:{channel_id}')
    return json.loads(redis_content) if redis_content else []
  
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
    if len(messages) > self.chat_max_length:
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
  parser.add_argument('--chat-channel-id', default=os.getenv('CHAT_CHANNEL_ID', ''), type=str)
  
  parser.add_argument('--bot-name', default=os.getenv('BOT_NAME', 'assistant'), type=str)
  parser.add_argument('--chat-max-length', default=os.getenv('CHAT_MAX_LENGTH', 500), type=int)
  parser.add_argument('--ctx', default=os.getenv('CTX', 2048), type=int)

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
    chat_channel_id = args.chat_channel_id,
    bot_name = args.bot_name,
    chat_max_length=args.chat_max_length,
    ctx=args.ctx,
  ).run(os.environ['DISCORD_TOKEN'])


if __name__ == '__main__':
  main()
