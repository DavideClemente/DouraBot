# DouraBot

## A discord bot made with discord.py

## Ready to deploy using docker

### Option 1:

#### Pull image from docker hub

> Pull docker image: docker pull davide2707clemente/dourabot:latest

#### Start MariaDb container

> docker run --detach -p 3306:3306 --name mariadoura --network douranetwork --env MARIADB_USER=dourabot --env MARIADB_PASSWORD=dourabot123 --env MARIADB_DATABASE=master --env MARIADB_ROOT_PASSWORD=dourabot123 mariadb:latest

#### Start python container

> docker run --name dourabot --network douranetwork -d davide2707clemente/dourabot:latest

### Option 2:

#### Run docker-compose file

> docker-compose up -d
