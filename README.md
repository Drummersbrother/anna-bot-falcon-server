# anna-bot-falcon-server
A falcon WSGI app for [anna-bot](https://github.com/drummersbrother/anna-bot "A discord bot called anna")

## How? What?
It's quite simple, [anna-bot](https://github.com/drummersbrother/anna-bot "A discord bot called anna") sends some data to the falcon app, and the falcon app serves it until it gets new data.  
It sends data with an accompanying token, for some simple auth.

## Ok, how2run?
You will need:  
#####Pypi:
```
falcon
jsonschema
```
#####Idk:
```
python3.5
A computer
Skillz
```
Just run the app (with 1 instance only since data is kept in ram, not files), and configure it with [anna's](https://github.com/drummersbrother/anna-bot "A discord bot called anna") `config.json`, and the app's `config.json`.

## Who?
Python code: [drummersbrother](https://github.com/drummersbrother "LOOK MOM, IT'S ME!").  
HTML and all the juicy design: [sade66](https://github.com/sade66 "Check him out").

# TL; DR:
We made a web app for a discord bot, use it.