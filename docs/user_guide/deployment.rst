Similar to Docker, PyroLab uses a single daemon process running in the 
background to manage all the processes. This daemon is started automatically 
when the first process is created.

Pyro5 is again utilized to run and communicate with PyroLab's daemon.

The PyroLab Daemon should be configured to run as a given user. This is because
PyroLab creates data and configuration file directories under the user's home
directory, instead of using obscure system directories that are OS-specific.
Whether configured as a Windows Task or a Linux cron job, PyroLab will
attempt to create these directories and files as the user that is running.
