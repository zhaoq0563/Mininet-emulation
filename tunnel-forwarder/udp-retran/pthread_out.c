#include "udpTunnel.h"

/**************************************************************************
 * pthread_out: tapTonet exits when receives signal.                      *
 **************************************************************************/

void pthread_out(int signo)
{
  pthread_exit(0);
}
