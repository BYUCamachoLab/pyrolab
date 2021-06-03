Shows the different behaviors of Pyro's server types.
First start the server, it will ask what type of server you want to run.
The client will print some information about what's happening.

Try it with different server types and see how that changes the behavior.

An example of an object that this would be useful for is a hardware motor.
You wouldn't want it receiving conflicting commands at the same time! Using the
"multiplex" option, all calls must get in line for processing. Hence, no two 
calls will ever walk on top of each other, but will be processed sequentially.