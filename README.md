# freqwatch
Simple tool to monitor multiple freqtrade bots and collect data from them.

## install dependencies
```
python -m pip install -r requirements.txt
```

## configuration

config.json should contain a list of running bots

```
{"bots":[
{
    "api_server": {
          "enabled": true,
          "listen_ip_address": "127.0.0.1",
          "listen_port": 8080,
          "username": "",
          "password": ""
     },
     "bot_name": "freqtrade" 
 }
]}
```

## running
```
./freqwatch.py
```
