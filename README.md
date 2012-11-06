# OVERVIEW
OpenStack Quantum has some problem when meta data fetching.
That's because instance has route route to meda-data api server. but the backward is not managed by quantum.

This agent manage the backward route from metadata to meta in external-router.

The agent assumes that external-router is linux box. this are generally applied to testing environment.
When production it will be hardware router.

# TODO
* apply rootwrapper for security
