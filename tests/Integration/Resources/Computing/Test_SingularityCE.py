#!/bin/env python

""" This integration test is for "Inner" Computing Element SingularityComputingElement
    This test is here and not in the unit tests because it requires singularity to be installed.
"""

import os
import shutil

from DIRAC import gLogger
from DIRAC.tests.Utilities.utils import find_all

from DIRAC.Resources.Computing.test.Test_PoolComputingElement import jobScript, _stopJob
from DIRAC.WorkloadManagementSystem.Utilities.Utils import createJobWrapper

# sut
from DIRAC.Resources.Computing.SingularityComputingElement import SingularityComputingElement


gLogger.setLevel("DEBUG")
fj = find_all("pilot.json", "../", "tests/Integration/Resources/Computing")[0]
fc = find_all("pilot.cfg.test", "../", "tests/Integration/Resources/Computing")[0]


def test_submitJob():
    shutil.copy(fj, os.curdir)
    shutil.copyfile(fc, os.path.join(os.curdir, "pilot.cfg"))
    with open("testJob.py", "w") as execFile:
        execFile.write(jobScript % "1")
    os.chmod("testJob.py", 0o755)

    ce = SingularityComputingElement("SingularityComputingElement")
    res = ce.submitJob("testJob.py", None)
    assert res["OK"] is False
    res = ce.getCEStatus()
    assert res["OK"] is True
    assert res["SubmittedJobs"] == 1
    _stopJob(1)
    for ff in ["testJob.py", "pilot.json"]:
        if os.path.isfile(ff):
            os.remove(ff)


def test_submitJobWrapper():
    with open("testJob.py", "w") as execFile:
        execFile.write(jobScript % "2")
    os.chmod("testJob.py", 0o755)

    jobParams = {"JobType": "User", "Executable": "testJob.py"}
    resourceParams = {"GridCE": "some_CE"}
    optimizerParams = {}

    result = createJobWrapper(
        jobID=2, jobParams=jobParams, resourceParams=resourceParams, optimizerParams=optimizerParams, logLevel="DEBUG"
    )["Value"]
    # To ensure backward compatiblitity in the test
    # The result was a tuple in the past and now is a dict
    if isinstance(result, dict):
        wrapperFile = result["JobExecutablePath"]
    else:
        wrapperFile = result[0]

    shutil.copy(fj, os.curdir)

    ce = SingularityComputingElement("SingularityComputingElement")
    res = ce.submitJob(
        wrapperFile,
        proxy=None,
        numberOfProcessors=4,
        maxNumberOfProcessors=8,
        wholeNode=False,
        mpTag=True,
        jobDesc={"jobParams": jobParams, "resourceParams": resourceParams, "optimizerParams": optimizerParams},
    )

    assert res["OK"] is False  # This is False because the image can't be found

    res = ce.getCEStatus()
    assert res["OK"] is True
    assert res["SubmittedJobs"] == 1

    _stopJob(2)
    for ff in ["testJob.py", "stop_job_2", "job.info", "std.out", "pilot.json"]:
        if os.path.isfile(ff):
            os.remove(ff)
    if os.path.isdir("job"):
        shutil.rmtree("job")
