# `docker-compose.yaml` Examples

> [!NOTE] 
> The container needs to run in `network_mode:"host"`. This also means that not all functionality is supported on a Windows host as Docker for Windows doesn't support this networking option. 

### Example 1

```yaml
services:
  netalertx:
    container_name: netalertx
    # use the below line if you want to test the latest dev image
    # image: "ghcr.io/jokob-sk/netalertx-dev:latest" 
    image: "ghcr.io/jokob-sk/netalertx:latest"      
    network_mode: "host"        
    restart: unless-stopped
    volumes:
      - local_path/config:/app/config
      - local_path/db:/app/db      
      # (optional) useful for debugging if you have issues setting up the container
      - local_path/logs:/app/log
      # (API: OPTION 1) use for performance
      - type: tmpfs
        target: /app/api
      # (API: OPTION 2) use when debugging issues 
      # -  local_path/api:/app/api
    environment:
      - TZ=Europe/Berlin      
      - PORT=20211
```

To run the container execute: `sudo docker-compose up -d`

### Example 2

Example by [SeimuS](https://github.com/SeimusS).

```yaml
services:
  netalertx:
    container_name: NetAlertX
    hostname: NetAlertX
    privileged: true
    # use the below line if you want to test the latest dev image
    # image: "ghcr.io/jokob-sk/netalertx-dev:latest" 
    image: ghcr.io/jokob-sk/netalertx:latest
    environment:
      - TZ=Europe/Bratislava
    restart: always
    volumes:
      - ./netalertx/db:/app/db
      - ./netalertx/config:/app/config
    network_mode: host
```

To run the container execute: `sudo docker-compose up -d`

### Example 3

`docker-compose.yml` 

```yaml
services:
  netalertx:
    container_name: netalertx
    # use the below line if you want to test the latest dev image
    # image: "ghcr.io/jokob-sk/netalertx-dev:latest" 
    image: "ghcr.io/jokob-sk/netalertx:latest"      
    network_mode: "host"        
    restart: unless-stopped
    volumes:
      - ${APP_CONFIG_LOCATION}/netalertx/config:/app/config
      - ${APP_DATA_LOCATION}/netalertx/db/:/app/db/      
      # (optional) useful for debugging if you have issues setting up the container
      - ${LOGS_LOCATION}:/app/log
      # (API: OPTION 1) use for performance
      - type: tmpfs
        target: /app/api
      # (API: OPTION 2) use when debugging issues 
      # -  local/path/api:/app/api
    environment:
      - TZ=${TZ}      
      - PORT=${PORT}
```

`.env` file

```yaml
#GLOBAL PATH VARIABLES

APP_DATA_LOCATION=/path/to/docker_appdata
APP_CONFIG_LOCATION=/path/to/docker_config
LOGS_LOCATION=/path/to/docker_logs

#ENVIRONMENT VARIABLES

TZ=Europe/Paris
PORT=20211

#DEVELOPMENT VARIABLES

DEV_LOCATION=/path/to/local/source/code
```

To run the container execute: `sudo docker-compose --env-file /path/to/.env up`


### Example 4: Docker swarm

Notice how the host network is defined in a swarm setup:

```yaml
services:
  netalertx:
    # Use the below line if you want to test the latest dev image
    # image: "jokobsk/netalertx-dev:latest"
    image: "ghcr.io/jokob-sk/netalertx:latest"
    volumes:
      - /mnt/MYSERVER/netalertx/config:/config:rw
      - /mnt/MYSERVER/netalertx/db:/netalertx/db:rw
      - /mnt/MYSERVER/netalertx/logs:/netalertx/front/log:rw
    environment:
      - TZ=Europe/London
      - PORT=20211
    networks:
      - outside
    deploy:
      mode: replicated
      replicas: 1
      restart_policy:
        condition: on-failure

networks:
  outside:
    external:
      name: "host"


```
