#include "udpTunnel.h"

/**************************************************************************
 * tapwrite: write routine to tap that checks for errors and exits if an  *
 *           error is returned.                                           *
 **************************************************************************/

int tapwrite(int fd, char *buf, int n){

  int nwrite;

  if((nwrite=write(fd, buf, n)) < 0){
    perror("Tap writing data");
    exit(1);
  }
  return nwrite;
}
