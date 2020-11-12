import json

eo_file = "../eo.txt"

# for firt 5 images
print("====================")
print(" * for firt 5 images")
print("====================")
ba = {}
with open(eo_file) as f:
    next(f)
    next(f)
    for line in f:
        params = line.split("\t")
        img_name = params[0]
        ba[img_name] = {}
        ba[img_name]['x'] = float(params[1])  # m
        ba[img_name]['y'] = float(params[2])  # m
        ba[img_name]['z'] = float(params[3])  # m
        ba[img_name]['o'] = float(params[4])  # deg
        ba[img_name]['p'] = float(params[5])  # deg
        ba[img_name]['k'] = float(params[6])  # deg
print(ba)

# for rest images
print("==================")
print(" * for rest images")
print("==================")
f = open(eo_file, 'r')
lines = f.readlines()
f.close()

ba2 = {}
ba2["x"] = float(lines[-1].split("\t")[1])     # m
ba2["y"] = float(lines[-1].split("\t")[2])     # m
ba2["z"] = float(lines[-1].split("\t")[3])     # m
ba2["o"] = float(lines[-1].split("\t")[4])     # deg
ba2["p"] = float(lines[-1].split("\t")[5])     # deg
ba2["k"] = float(lines[-1].split("\t")[6])     # deg
print(ba2)

print("Done")
