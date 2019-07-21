#include "udpTunnel.h"

/**************************************************************************
 * do_debug: prints debugging stuff (doh!)                                *
 **************************************************************************/

void do_debug(char *msg, ...){

  va_list argp;

  if(debug) {
    va_start(argp, msg);
    vfprintf(stderr, msg, argp);
    va_end(argp);
  }
}
