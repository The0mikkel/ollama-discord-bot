# Ollama discord chatbot

This Discord chatbot is built to follow the chat flow and have a conversation with the user. The bot is built using the discord.py library, and the chat is stored in Redis. The number of messages to have in context is configurable.

## Installation

0. Have [Ollama](https://ollama.com) and [Docker](https://docker.com) installed and running
1. Clone the repository
2. Configure the `.env` file with at least the following variables (see [Configuration](#configuration) for more options):
    - `DISCORD_TOKEN`: The token of the discord bot (token can be obtained from the [Discord Developer Portal](https://discord.com/developers/applications))
    - `ADMIN_ID`: The id of the admin user, which allows to RESET the chat
3. Run `docker-compose up -d` to start the bot
4. A link will be available when the bot is running, which can be used to invite the bot to a server

*This will use the Ollama installed and running on your system. This will therefore allow for people to use ressources on your machine. If you want to use a different Ollama instance, you can set the `OLLAMA_SCHEME`, `OLLAMA_HOST` and `OLLAMA_PORT` variables in the `.env` file.*

### Running used pre-built image

The project provides a pre-built image, which can be used to run the bot. This is useful if you do not want to build the image yourself.

Image is available at `ghcr.io/the0mikkel/ollama-discord-bot:latest`.

A provided [docker-compose.prod.yml](docker-compose.prod.yml) file can be used to run the bot using the pre-built image.  
Just copy it to `docker-compose.yml` and run `docker-compose up -d`.

## Features

The bot listen in and is able to have a conversation with the user. The bot has the whole chat flow of a single channel. This means, even though the bot is not interacted with, it can be called in, and have the previous messages in context.

The bot is built to be a chatbot. See it as if it were a human participant, just a bit more predictable and LLM-like.

## Commands

If you are the admin, you can reply to it and write `RESET` to reset the chat. This is useful if you want to start the chat from the beginning.
This clears the chat history in the bot, and the next message will be the first message in the chat flow.

The message has to be exactly `RESET`, and the bot will not reply to it.

## Interaction

The bot will reply to messages, which mentions it. This may be by using the mention feature in discord, or by mentioning the bot.

## Configuration

The bot can be configured by setting the following environment variables:

- `DISCORD_TOKEN`: Your Discord bot token. This is required for the bot to connect to Discord.
- `OLLAMA_SCHEME`: The scheme for the Ollama API (http or https).
- `OLLAMA_HOST`: The host for the Ollama API.
- `OLLAMA_PORT`: The port for the Ollama API.
- `OLLAMA_MODEL`: The model to use for the Ollama API.
- `REDIS_HOST`: The host for the Redis server.
- `REDIS_PORT`: The port for the Redis server.
- `ADMIN_ID`: The Discord ID of the admin user. This user will have the ability to reset the chat.
- `BOT_NAME`: The name of the bot. This is used for the bot to recognize when it is mentioned in a message.
- `CHAT_MAX_LENGTH`: The maximum length of the chat history to store in Redis. This is used to limit the amount of memory used by the bot.
- `CTX`: The context length for the Ollama API. This determines how much of the chat history the bot will consider when generating a response.

## Security

**Always be cautious when running this bot.**

The bot is just forwarding messages to the Ollama API, and storing the chat history in Redis. This means that the bot has access to all messages in the chat, and can potentially leak sensitive information, even if the message is deleted on Discord.

Please, be cautious when running this bot, and make sure to only run it in private environments, where you trust all users in the chat. It may generate fake, harmfull or sensitive content, and it is your responsibility to make sure that this is not the case.

**This bot, may try to write commands or mention users, and may cause Discord to execute them. Please do not give more permissions than necessary to the bot.**

## Models

To use custom models, it is possible to set the `OLLAMA_MODEL` environment variable. This will allow you to use any model that is available in the Ollama API. The default model is `llama3`.

It is **recommended** to use a custom model, to get the best chatting experience. The default model is not trained on the chat flow, and may not generate good responses.

You can use [OpenWebUI](https://github.com/open-webui/open-webui) to configure and interact with the Ollama API. It is also a nice web panel for the system, if you were looking for a web-specific system.

### Example model

An example of a custom model is listed below:

```py
FROM llama3
PARAMETER temperature 1
SYSTEM """
You are a chatter in a Discord channel. Your goal is to respond like you were a human, and fit into the chat.
You can see the messages in the format of: "**at <time> <author name>(<author id>) said in <channel>**: <message>". 
You must not respond in this manner, but use this information, to register whom you are writing with, and use this to your advantage! 
So answer without "**at <time> <author name>(<author id>) said in <channel>**" format! This is very important.
Multiple people will write to you at once, so this is important!
Your name is Assistant.
"""
```

*Replace "Assistant" with the name of the bot, and get a better experience.*

## Compatibility

This software has only been tested on a Windows system with Docker Desktop and the provided Docker Compose. It should work on other systems, but it is not guaranteed.

## Credits

This is based on [mxyng/discollama](https://github.com/mxyng/discollama), but is heavily modified to fit the needs of a chatbot, rather than a response generator.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

If you want to contribute to this project, you are more than welcome.  
However, the project does use [semver](https://semver.org) for versioning, and the [conventional commits](https://www.conventionalcommits.org) for commit messages throug [semantic-release](https://github.com/semantic-release/semantic-release).

Please see the [CONTRIBUTING](CONTRIBUTING.md) file for more information.

## Author

This project is made by [Mikkel Albrechtsen](https://github.com/the0mikkel).
