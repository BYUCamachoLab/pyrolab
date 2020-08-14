This example shows the use of the instance_mode option when exposing a class.

Even with single instance mode, different threads can call the same object
concurrently. Make sure the object is safe to be called from different places!

An example of an object that this would not be safe with is a hardware motor.
You wouldn't want it receiving conflicting commands at the same time! For such
a use case, refer to the `servertypes` example.