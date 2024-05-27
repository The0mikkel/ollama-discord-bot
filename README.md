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

## Credits

This is based on [mxyng/discollama](https://github.com/mxyng/discollama), but is heavily modified to fit the needs of a chatbot, rather than a response generator.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

This project is made by [Mikkel Albrechtsen](https://github.com/the0mikkel).
