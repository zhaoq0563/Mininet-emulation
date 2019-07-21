#include "udpTunnel.h"

/**************************************************************************
 * cread: read routine that checks for errors and exits if an error is    *
 *        returned.                                                       *
 **************************************************************************/

int cread(int fd, struct sockaddr_in *si, char *buf, int n){

  int nread;
  unsigned int len = sizeof(*si);

  if((nread=recvfrom(fd, buf, n, MSG_WAITALL, si, &len)) < 0){
    perror("Reading data");
    exit(1);
  }

  return nread;
}
