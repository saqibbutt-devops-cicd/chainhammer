docker ps -aq | xargs -r docker rm -f
docker images -q chainhammer | xargs -r docker rmi -f
docker builder prune -af
docker system prune -af --volumes


export DOCKER_DEFAULT_PLATFORM=linux/amd64

docker build --no-cache -t chainhammer:local .

docker run --rm \
-e CH_RPC="http://localhost:8545" \
-e CH_TXS=10 \
-e CH_THREADING=sequential \
-v "$PWD/logs:/opt/chainhammer/logs" \
chainhammer:local quick