Operations / VOs - Subsections
==============================

<VO_NAME> subsections allows to define pilot jobs DIRAC versions for each VO supported by the server.

+-----------------------------------------------+----------------------------------------------+---------------------------+
| **Name**                                      | **Description**                              | **Example**               |
+-----------------------------------------------+----------------------------------------------+---------------------------+
| *<VO_NAME>*                                   | Subsection: Virtual organization name        | vo.formation.idgrilles.fr |
+-----------------------------------------------+----------------------------------------------+---------------------------+

This section will progressively incorporate most of the other sections under /Operations in such a way
that different values can be defined for each [VO] (in multi-VO installations). A helper
class is provided to access to these new structure.

::
  from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations
  op = Operations()
  op.getSections('Dirac-Production', '')
