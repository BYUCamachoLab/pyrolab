import urllib.request

with urllib.request.urlopen("https://camacholab.ee.byu.edu/CamachoLab/5ce45ff92b11250f5d1b44cc/page") as url:
    s = url.read()
    # I'm guessing this would output the html source code ?
    print(s)