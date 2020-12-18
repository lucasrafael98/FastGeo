# FastGeo Guide

This guide covers the project structure of FastGeo. If any details elude you, please read the [dissertation](FastGeo.pdf).

## Structure

FastGeo is an Express project, so the structure is similar, except for the ``preprocess`` and ``data`` folders:

```
fastgeo
    |- bin
    |- data (doesn't show up on the repository)
    |- preprocess
    |- public
    |   |- javascripts
    |   |- stylesheets
    |   |- vendor 
    |- routes
    |   |- _aux
    |   |- stream
    |   |   |- modules
    |- views

```

The ``views`` folder contains the front end views, which use JavaScript and CSS code from the ``public`` folder. 

The ``routes`` folder contains back end JavaScript code. ``index.js`` handles front end requests, and starts the streaming simulation loop, which is implemented in ``stream/manager.js``. Time period modules inherit the base code from ``stream/modules/stream_module.js``. The ``_aux`` folder contains code for child process creation.

The ``preprocess`` folder contains all Python code. Files named ``module_*.py`` correspond to the Python side of the time period modules, and they communicate with JavaScript and call preprocessing methods found in the other files.

The ``data`` folder contains, obviously, data. The simulation takes as starting input whatever is on the ``raw`` folder. If you want to use a different dataset than the one used for this thesis, you may need to implement custom parsing for it in ``prepreocessing/initial_parsing.py`` so that the dataset is converted properly into something the simulation can use, though you won't have to change anything else.

Alternatively, you can set up a ``resumeFolder`` in ``config.yaml``. These resume folders are created by simply stopping the simulation, which creates a ``last`` folder which you can then use to resume the simulation from the point at which you stopped.

Each simulation step, the manager (``routes/stream/manager.js``) will grab the data fetched by the ``rawFetchLoop()``, and perform the three sub-steps by asynchronously calling each module's ``removeData()`` function, creating three promises, all of which the manager will wait for before then doing the same for ``updateData()``, and then for ``displayData()``.

After the ``displayData()`` methods end, the manager will join all the data that these return into ``data/temp/update.json``, which is sent to the front end when requested. If the front end requests the same file twice (which happens if a simulation step has taken longer than the interval for front end requests), it will ignore the second/third/etc. time this file is sent.

## Creating a new time period

To create a new time period, do the following:

- Create a new class in ``routes/stream/modules`` inheriting from the base interface
- Implement removal/update/display methods (more on this below)
- Create a ``module_<modulename>.py`` file to handle data processing
- Make sure you are instancing a class of your new module and calling its methods in ``manager.js``
- Implement the Mapbox layer/source for the data it sends through ``update.json`` in the front end.

The removal/update/display methods in the JavaScript module code all follow the same basic structure. You'll want to return a Promise (so that the simulation manager can wait for the method to be done), and then you'll do the following before resolving the promise:

```javascript
this.childProcess.stdin.write(`['<command>', <arg1>, <arg2>, ...]\n`, "utf-8");
let promise = new Promise((resolve, reject)=>{this.continue = resolve;})
await promise;
```

For each Python module, the basic code is:

```python
while(keep_running):
    next_command = eval(input())
    if(next_command[0] == "<command1>"):
        do_something(next_command[1:])
    elif(next_command[0] == "<command2>"):
        do_something_else(next_command[1:])
    (...)
    print('_')
```

In each module, ``this.childProcess`` is its corresponding Python process. Communication is done by simple ``stdin/stdout``. The JavaScript module writes a command in the Python process's ``stdin``, which accepts the command with ``input()`` and does different things depending on it. After performing the command, it ``print()``s an underscore ``'_'``, which the JavaScript module takes as a signal that it can resolve its promise and let the simulation manager continue to the next step. If you wish to use prints in the Python code, they will appear in the terminal (just don't start the print with ``'_'``, obviously).