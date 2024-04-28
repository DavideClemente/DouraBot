# DouraBot

![discord](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)
![python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
![docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)
![mariadb](https://img.shields.io/badge/MariaDB-003545?style=for-the-badge&logo=mariadb&logoColor=white)

## A discord bot made with discord.py

This is a custom bot made for my discord server using the discord.py library. Includes features such as:

-   Imdb library search
-   Currency conversion
-   Music player
-   Birthday reminder

**Disclaimer!!** - This bot only works with my specific discord server due to custom channel names, roles, etc.

## Table of Contents

-   [DouraBot](#dourabot)
    -   [A discord bot made with discord.py](#a-discord-bot-made-with-discordpy)
    -   [Table of Contents](#table-of-contents)
    -   [Installation](#installation)
        -   [Using dockerfile](#using-dockerfile)
            -   [Pull image from docker hub](#pull-image-from-docker-hub)
            -   [Start MariaDb container](#start-mariadb-container)
            -   [Start python container](#start-python-container)
        -   [Using docker-compose:](#using-docker-compose)
            -   [Run docker-compose file](#run-docker-compose-file)

## Installation

### Using dockerfile

#### Pull image from docker hub

```batch
docker pull davide2707clemente/dourabot:latest
```

#### Start MariaDb container

```batch
docker run --detach -p 3306:3306 --name mariadoura --network douranetwork --env MARIADB_USER=dourabot --env MARIADB_PASSWORD=dourabot123 --env MARIADB_DATABASE=master --env MARIADB_ROOT_PASSWORD=dourabot123 mariadb:latest
```

#### Start python container

```batch
docker run --name dourabot --network douranetwork -d davide2707clemente/dourabot:latest
```

### Using docker-compose:

#### Run docker-compose file

```batch
docker-compose up -d
```
