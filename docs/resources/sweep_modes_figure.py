import matplotlib.pyplot as plt

fig, ax = plt.subplots(3, 2)

y_axis = "frequency"

x = [1, 2, 3, 4, 5, 5, 6, 7, 8, 9, 9]
y = [0, 1, 2, 3, 4, 0, 1, 2, 3, 4, 0]
ax[0, 0].plot(x, y)
ax[0, 0].set_ylabel(y_axis)
ax[0, 0].set_xlabel("duration")
ax[0, 0].set_yticklabels([])
ax[0, 0].set_xticklabels([])
ax[0, 0].set_title("Continuous, one-way")

x = [1, 2, 3, 4, 5, 6, 7, 8, 9]
y = [0, 2, 4, 2, 0, 2, 4, 2, 0]
ax[0, 1].plot(x, y)
ax[0, 1].set_ylabel(y_axis)
ax[0, 1].set_xlabel("duration")
ax[0, 1].set_yticklabels([])
ax[0, 1].set_xticklabels([])
ax[0, 1].set_title("Continuous, two-way")

x = [1, 2, 3, 4, 5, 5, 6, 7, 8, 9, 9]
y = [0, 1, 2, 3, 3, 0, 1, 2, 3, 3, 0]
ax[1, 0].step(x, y, where="post")
ax[1, 0].set_ylabel(y_axis)
ax[1, 0].set_xlabel("duration")
ax[1, 0].set_yticklabels([])
ax[1, 0].set_xticklabels([])
ax[1, 0].set_title("Stepwise, one-way")

x = [1, 2, 3, 4, 5, 5, 6, 7, 8, 9, 10, 11, 12, 13]
y = [0, 1, 2, 3, 3, 2, 1, 0, 1, 2, 3, 2, 1, 0]
ax[1, 1].step(x, y, where="post")
ax[1, 1].set_ylabel(y_axis)
ax[1, 1].set_xlabel("duration")
ax[1, 1].set_yticklabels([])
ax[1, 1].set_xticklabels([])
ax[1, 1].set_title("Stepwise, two-way")

x = [1, 2, 3, 3, 4, 5, 6, 6, 7]
y = [0, 2, 4, 0, 0, 2, 4, 0, 0]
ax[2, 0].plot(x, y)
ax[2, 0].set_ylabel(y_axis)
ax[2, 0].set_xlabel("duration")
ax[2, 0].set_yticklabels([])
ax[2, 0].set_xticklabels([])
ax[2, 0].set_title("Continuous, one-way, delay")

x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
y = [0, 2, 4, 2, 0, 0, 2, 4, 2, 0, 0]
ax[2, 1].plot(x, y)
ax[2, 1].set_ylabel(y_axis)
ax[2, 1].set_xlabel("duration")
ax[2, 1].set_yticklabels([])
ax[2, 1].set_xticklabels([])
ax[2, 1].set_title("Continuous, two-way, delay")

plt.tight_layout()
plt.show()
