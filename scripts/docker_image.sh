docker-compose down
docker rmi tasks
git pull
docker-compose up -d
docker logs -f tasks
