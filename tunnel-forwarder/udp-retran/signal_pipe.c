#include "udpTunnel.h"

/**************************************************************************
 * signal_pipe: netTotap receives signal SIGPIPE when tapTonet breaks     *
 *              and netTotap sends SIGQUIT signal to tapTonet.            *
 **************************************************************************/

void signal_pipe(int signo)
{
  pthread_kill(tapTonet_id,SIGQUIT);
  pthread_join(tapTonet_id,NULL);

  perror("tapTonet pthread out \n");

  pthread_exit(0);
}

