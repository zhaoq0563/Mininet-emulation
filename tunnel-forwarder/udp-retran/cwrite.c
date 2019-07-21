#include "udpTunnel.h"

/**************************************************************************
 * cwrite: write routine that checks for errors and exits if an error is  *
 *         returned.                                                      *
 **************************************************************************/

int cwrite(int fd, struct sockaddr_in *si, char *buf, int n){

  int nwrite;

  if((nwrite=sendto(fd, buf, n, MSG_CONFIRM, si, sizeof(*si))) < 0){
    perror("Writing data");
    exit(1);
  }
  return nwrite;
}
