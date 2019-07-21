#include "udpTunnel.h"

/**************************************************************************
 * my_err: prints custom error messages on stderr.                        *
 **************************************************************************/

void my_err(char *msg, ...) {

  va_list argp;

  va_start(argp, msg);
  vfprintf(stderr, msg, argp);
  va_end(argp);
}
