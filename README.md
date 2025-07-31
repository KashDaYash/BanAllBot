# BanAllBot

A Telegram bot to mass-ban users from groups.  
Built with [Pyrogram](https://github.com/pyrogram/pyrogram).

## Features

- `/banall`: Ban all members in a group (admin only)
- `/start`: Check if bot is alive

## Deploy

### Heroku
<h3 align="center">
    ─「 ᴅᴇᴩʟᴏʏ ᴏɴ ʜᴇʀᴏᴋᴜ 」─
</h3>

<p align="center"><a href="https://www.heroku.com/deploy?template=https://github.com/KashDaYash/BanAllBot">
  <img src="https://www.herokucdn.com/deploy/button.svg" alt="Deploy">
</a> <img src="https://img.shields.io/badge/Deploy%20On%20Heroku-Purple?style=for-the-badge&logo=heroku" width="220" height="38.45"/></a></p>

1. Click on "Deploy to Heroku" or use:
2. Set `API_ID`, `API_HASH`, `BOT_TOKEN` in Heroku Config Vars.
3. Done!

### Docker

```bash
docker build -t banallbot .
docker run -e API_ID=xxx -e API_HASH=xxx -e BOT_TOKEN=xxx banallbot
```

## Environment Variables

- `API_ID`: Your Telegram API ID
- `API_HASH`: Your Telegram API Hash
- `BOT_TOKEN`: Your Telegram Bot Token

## Credits

- [Pyrogram](https://github.com/pyrogram/pyrogram)
