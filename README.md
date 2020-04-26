# usm-archive-builder
## Information
This is a microservice built to create prebuilt and encrypted bannerbomb3 payloads for use with the unSAFE_MODE method.
## Requirements
- Docker
## Install Instructions
First you need to build the docker image.
```
docker build . -t deadphoenix8091/usm-archive-builder
```

Then you need to run the docker image. 

```
docker run -it -p 80:80 deadphoenix8091/usm-archive-builder .
```
