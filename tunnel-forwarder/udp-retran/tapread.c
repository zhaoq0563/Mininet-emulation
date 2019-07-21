#include "udpTunnel.h"

/**************************************************************************
 * tapread: read routine from tap that checks for errors and exits if an  *
 *          error is returned.                                            *
 **************************************************************************/

int tapread(int fd, char *buf, int n){

  int nread;

  if((nread=read(fd, buf, n)) < 0){
    perror("Tap reading data");
    exit(1);
  }
  return nread;
}
