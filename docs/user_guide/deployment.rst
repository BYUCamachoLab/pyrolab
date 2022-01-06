.. _user_guide_deployment:


Deployment
==========

Similar to Docker, PyroLab uses a single daemon process running in the 
background to manage all the processes. This daemon is started automatically 
when the first process is created.

Pyro5 is again utilized to run and communicate with PyroLab's daemon.

The PyroLab Daemon should be configured to run as a given user. This is because
PyroLab creates data and configuration file directories under the user's home
directory, instead of using obscure system directories that are OS-specific.
Whether configured as a Windows Task or a Linux cron job, PyroLab will
attempt to create these directories and files as the user that is running.

PyroLab can be configured to automatically launch at startup. The process is
different based on operating system.

Operating Systems
-----------------

Windows
^^^^^^^

Write a batch file (or use the one located in pyrolab/bin/pyrolab.bat) that
launches PyroLab. Depending on whether you're using a base python or conda
for your environment, you may need to activate environments accordingly. 

Note that in the example file provided, the "--force" option is used. We assume
this script will only be run on startup, therefore even if the application did
not clean up properly, we can be guaranteed that it isn't already running and
overwriting the lockfile is safe. Be aware that this is what's happening if 
you decide to debug your batch file; you may be creating a bunch of orphaned
processes!

Once the batch file is written, you have two options. You can configure Windows
to run the file as a task on a schedule (in our case, on startup), which should
in theory work even if no one logs in to the computer, but it is simply 
restarted. This is nice in a lab, if you're not actually using the computer
hosting various PyroLab services; you can just start the computer by pressing
the power button and not worry about logging in on each computer that hosts a 
service you need. For example, many of our computers run "headless," without a
monitor attached, and it would be a hassle to remote into every machine after
startup just to login. The second option is to place the .bat file in the 
Startup folder. These only get launched on login, however. Instructions for 
both methods are included below.

Using the Task Scheduler
""""""""""""""""""""""""

1. Open the Windows Task Scheduler.
2. Create a new basic task.
3. Name it something recognizable, like "pyrolabd". Optionally, add a 
   description.
4. Set the trigger time to "When the computer starts".
5. Set the action to "Start a program".
6. Find the batch file location, place that in "Program/script".
7. Select "Open the Properties dialog..." before clicking Finish, or open the
   Properties dialog manually by selecting it from the list of scheduled tasks.
8. Under "General", ensure that it's running under some User's account.
9. Additionally, select, "Run whether user is logged on or not" (note: do NOT
   select "Do not store password.").
10. Select "Run with highest privileges".
11. Under "Conditions", deselect all (for example, we always want the task
    to start, regardless of battery state or the computer being idle).
12. Under "Settings", select "Allow task to be run on demand", "Run task as 
    soon as possible after a scheduled start is missed", and "If the 
    running task does not end when requested, force it to stop".

Using the Startup folder
""""""""""""""""""""""""

1. Press the Windows+R key to open the run dialog.
2. Type "shell:startup" and press Enter.
3. Right click in the folder and select "New".
4. Click "Shortcut".
5. Type the location of the batch file, or browse to it.
6. Click "Next".
7. Type a name for the shortcut (such as "pyrolabd"), and click "Finish".

macOS
^^^^^

Your mac os crontab as well.

Linux
^^^^^

The easiest way to run pyrolabd is by running a cron job set to run at startup.

Starting the Daemon
-------------------

PyroLab has a constantly-running daemon process in the background that monitors
Pyro services and awaits user commands via the command line interface (CLI). 
The CLI is really just a glorified client; the PyroLab daemon is listening 
on some localhost port, and the CLI simply sends commands to the daemon. The
CLI is not the instance of PyroLab that is actually managing what would be 
considered the "PyroLab program."

Launching from the command line
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To start the daemon, simply run the following command:

.. code-block:: bash

   pyrolab up

If PyroLab has been configured with a user-defined file, the daemon will
automatically load that configuration. (This does not imply that all the 
listed services will be started; for that to happen, they must be listed in
the ``autolaunch`` section of the configuration file.)

Force launching the daemon
^^^^^^^^^^^^^^^^^^^^^^^^^^

PyroLab does its very best to ensure that only one instance of the background
daemon is running. It creates a lockfile when it's started, and no other 
instances can be created if that lockfile exists. Anytime the daemon is
shut down, the lockfile is deleted.

The reason there should only be one instance of PyroLab should be obvious;
if there are subsequent instances started, all prior instances will in effect
be "orphaned;" PyroLab will have no knowledge of their existence, and they'll
continue on, hogging resources (and potentially blocking access to hardware
devices or other single-access resources), unable to be shutdown by PyroLab.
PyroLab therefore only allows one instance to be started.

There may be, however, rare instances where an error occurs, so egregious that
Python terminates immediately, without getting a chance to run the "cleanup"
code. In such cases, PyroLab may think that an instance is running when it 
really isn't. The CLI does have an option to force start a new daemon, which 
will overwrite the lockfile and "forget" about any previous running instances.
You should double check that the daemon actually died before force starting
a new one (either in Windows' Task Manager, Mac OS's Activity Monitor, or 
perhaps in the terminal). To force start a new daemon, simply run:

.. code-block:: python

   pyrolab up --force
