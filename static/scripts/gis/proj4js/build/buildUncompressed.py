#!/usr/bin/env python

import sys
sys.path.append("../tools")

import jsmin, mergejs

sourceDirectory = "../lib"
configFilename = "library.cfg"
outputFilename = "../lib/proj4js-combined.js"

if len(sys.argv) > 1:
    configFilename = sys.argv[1] + ".cfg"
if len(sys.argv) > 2:
    outputFilename = sys.argv[2]

print "Merging libraries."
merged = mergejs.run(sourceDirectory, None, configFilename)
print "Adding license file."
merged = file("license.txt").read() + merged

print "Writing to %s." % outputFilename
file(outputFilename, "w").write(merged)

print "Done."
