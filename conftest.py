# The bayta/ application manages its own virtualenv, dependencies and test
# suite (see bayta/Makefile); keep repository-wide pytest runs out of it.
collect_ignore = ["bayta"]
