""" srun parallel library

Allow to wrap a job/pilot into a srun call that will execute n similar tasks in parallel.
To work, srun needs to be used in conjonction with Slurm.
"""
import os
import stat
from six.moves import shlex_quote

from DIRAC.Resources.Computing.ParallelLibraries.ParallelLibrary import ParallelLibrary


class Srun(ParallelLibrary):

  def __init__(self, workingDirectory):
    super(Srun, self).__init__('srun', workingDirectory)

  def generateWrapper(self, executableFile):
    """
    Associate the executable with srun, to execute the same command in parallel on multiple nodes.
    Wrap it in a new executable file

    :param str executableFile: name of the executable file to wrap
    :return str: name of the wrapper that runs the executable via srun
    """
    # As the executable will be executed by srun, it needs GRP and OTH execution permission
    if not os.access(executableFile, os.R_OK | os.X_OK):
      os.chmod(executableFile, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    # Build the script to run the executable in parallel multiple times
    # srun is the command to execute a task multiple time in parallel
    # -l option: add the task ID to the output
    # -k option: do not kill the slurm job if one of the nodes is broken
    cmd = '#!/bin/bash\n'
    cmd += 'srun -l -k %s' % shlex_quote(executableFile)
    self.log.debug("Command generated by Srun:", "%s" % cmd)

    srunWrapper = os.path.join(self.workingDirectory, 'srunExec.sh')
    with open(srunWrapper, 'w') as exe:
      exe.write(cmd)
    if not os.access(srunWrapper, os.R_OK | os.X_OK):
      os.chmod(srunWrapper, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH + stat.S_IXOTH)
    return srunWrapper

  def processOutput(self, output, error, isFile=True):
    """
    Reorder the content of the output files according to the node identifier.

    From:
    >>> 1: line1
    >>> 2: line1
    >>> 1: line2
    To:
    >>> # On node 1
    >>>   line1
    >>>   line2
    >>> # On node 2
    >>>   line1

    :param str output: name of the output file, or its content
    :param str error: name of the error file, or its content
    :param bool isFile: indicates if the inputs represent files or content of the files
    """
    if isFile:
      self._openFileAndSortOutput(output)
      self._openFileAndSortOutput(error)
    else:
      output = self._sortOutput(output)
      error = self._sortOutput(error)
    return (output, error)

  def _openFileAndSortOutput(self, outputFile):
    """
    Open a file, get its content and reorder it according to the node identifiers

    :param str outputFile: name of the file to sort
    """
    with open(outputFile, 'r') as f:
      outputContent = f.read()

    sortedContent = self._sortOutput(outputContent)

    with open(outputFile, 'w') as f:
      f.write(sortedContent)

  def _sortOutput(self, outputContent):
    """
    Reorder the content of the output file according to the node identifiers

    :param str outputContent: content to sort
    :return str: content sorted
    """
    outputLines = outputContent.split('\n')
    nodes = {}
    for line in outputLines:
      node, line_content = line.split(':', 1)
      if node not in nodes:
        nodes[node] = []
      nodes[node].append(line_content)

    content = ''
    for node, lines in nodes.items():
      content += "# On node %s\n\n" % node
      content += '\n'.join(lines) + '\n'
    return content
