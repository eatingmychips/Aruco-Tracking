import numpy as np
import matplotlib.pyplot as plt

image_height = 200
image_length = 300

# Generate parameter t for one full sine cycle
t = np.linspace(0, 2 * np.pi, 100)

# x runs from 50 to image_length - 50
x = 50 + (image_length - 100) * t / (2 * np.pi)

# y is a sine wave with amplitude image_height
y = 100 + (image_height/2 - 50) * np.sin(t)

# Create shifted sine waves
y_above = y + 20
y_below = y - 20

# Plot the result
plt.figure(figsize=(10, 5))
plt.plot(x, y, 'ob', label='Original points')  # Main sine wave (blue dots)
plt.plot(x, y_above, 'r:', label='Above (+20)', linewidth=2)  # Dotted red above
plt.plot(x, y_below, 'g:', label='Below (-20)', linewidth=2)  # Dotted green below

plt.title("Sine Wave With Dotted Above and Below")
plt.xlabel("x")
plt.ylabel("y")
plt.xlim(0, 300)
plt.ylim(0, 200)
plt.legend()
plt.grid(True)
plt.show()
