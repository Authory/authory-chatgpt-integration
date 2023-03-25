# Getting started 

Set up redis: 

```
docker run -d --name authory-vector-redis -p 6379:6379 -v redis_data:/home/emi/Projects/authory-chatgpt-integration/data redis/redis-stack-server:latest
```

Set up python package manager:

```
sudo pip install poetry
```

Run:

```
poetry start
```