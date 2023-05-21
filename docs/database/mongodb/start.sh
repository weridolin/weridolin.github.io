docker-compose -f fates-mongo-compose.yaml exec config1 bash -c "echo 'rs.initiate({_id: \"fates-mongo-config\",configsvr: true, members: [{ _id : 0, host : \"config1:27019\" },{ _id : 1, host : \"config2:27019\" }, { _id : 2, host : \"config3:27019\" }]})' | mongo --port 27019"
docker-compose -f fates-mongo-compose.yaml exec shard1 bash -c "echo 'rs.initiate({_id: \"shard1\",members: [{ _id : 0, host : \"shard1:27018\" }]})' | mongo --port 27018"
docker-compose -f fates-mongo-compose.yaml exec shard2 bash -c "echo 'rs.initiate({_id: \"shard2\",members: [{ _id : 0, host : \"shard2:27018\" }]})' | mongo --port 27018"
docker-compose -f fates-mongo-compose.yaml exec shard3 bash -c "echo 'rs.initiate({_id: \"shard3\",members: [{ _id : 0, host : \"shard3:27018\" }]})' | mongo --port 27018"
docker-compose -f fates-mongo-compose.yaml exec mongos bash -c "echo 'sh.addShard(\"shard1/shard1:27018\")' | mongo"
docker-compose -f fates-mongo-compose.yaml exec mongos bash -c "echo 'sh.addShard(\"shard2/shard2:27018\")' | mongo"
docker-compose -f fates-mongo-compose.yaml exec mongos bash -c "echo 'sh.addShard(\"shard3/shard3:27018\")' | mongo"


docker exec -it   config1 mongosh --eval "rs.initiate(
  {
    _id: "configsrv",
    configsvr: true,
    members: [
      { _id : 0, host : "config1" },
      { _id : 1, host : "config2" },
      { _id : 2, host : "config3" }
    ]
  }
)"

rs.initiate(
  {
    _id: "shard3",
    members: [
      { _id : 0, host : "shard3" }
    ]
  }
)
