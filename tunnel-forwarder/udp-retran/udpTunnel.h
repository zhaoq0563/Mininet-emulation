#ifndef UDPTUNNEL_H_INCLUDED
#define UDPTUNNEL_H_INCLUDED

#define _GNU_SOURCE

#include <arpa/inet.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/if_tun.h>
#include <math.h>
#include <net/if.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/select.h>
#include <sys/time.h>
#include <termios.h>
#include <unistd.h>
#include <stdint.h>

/* buffer for reading from tun/tap interface, must be >= 1500 */
#define BUFSIZE 2020
#define HEADERSIZE 11u
#define CLIENT 0
#define SERVER 1
#define PORT 10086
#define SHAPINGDELAY 800000
#define RTD 400000

extern int debug;
extern char *progname;
extern pthread_t tapTonet_id, netTotap_id;

struct fds {
  int *tap;
  int *net;
  struct sockaddr_in *servaddr;
  struct sockaddr_in *clitaddr;
  char *pAckbuf;
  uint16_t *nread;
};

struct retranPar {
  int *net;
  struct sockaddr_in *targetAddr;
  char *pAckbuf;
  char *dataBuf;
  uint16_t *nread;
};

struct thdPar {
  int      *net;
  uint16_t *plength;
  char     *buffer;
  long int *time;
};

struct pkHeader {
    uint8_t dataType;
    unsigned short int pkID;
    long int timeStamp;
};

/**************************************************************************
 * do_debug: prints debugging stuff (doh!)                                *
 **************************************************************************/
void do_debug(char *msg, ...);

/**************************************************************************
 * tun_alloc: allocates or reconnects to a tun/tap device. The caller     *
 *            must reserve enough space in *dev.                          *
 **************************************************************************/
int tun_alloc(char *dev, int flags);

/**************************************************************************
 * cread: read routine that checks for errors and exits if an error is    *
 *        returned.                                                       *
 **************************************************************************/
int cread(int fd, struct sockaddr_in *si, char *buf, int n);

/**************************************************************************
 * cwrite: write routine that checks for errors and exits if an error is  *
 *         returned.                                                      *
 **************************************************************************/
int cwrite(int fd, struct sockaddr_in *si, char *buf, int n);

/**************************************************************************
 * tapread: read routine from tap that checks for errors and exits if an  *
 *          error is returned.                                            *
 **************************************************************************/
int tapread(int fd, char *buf, int n);

/**************************************************************************
 * tapwrite: write routine to tap that checks for errors and exits if an  *
 *           error is returned.                                           *
 **************************************************************************/
int tapwrite(int fd, char *buf, int n);

/**************************************************************************
 * sendToTap: send the packet to the tap interface with delay.            *
 **************************************************************************/
void* sendToTap(void *arg);

/**************************************************************************
 * signal_pipe: netTotap receives signal SIGPIPE when tapTonet breaks     *
 *              and netTotap sends SIGQUIT signal to tapTonet.            *
 **************************************************************************/
void signal_pipe(int signo);

/**************************************************************************
 * pthread_out: tapTonet exits when receives signal.                      *
 **************************************************************************/
void pthread_out(int signo);

/**************************************************************************
 * tapTonet_c: Tap interface to Net interface pthread for client.         *
 **************************************************************************/
void* tapTonet_c(void *input);

/**************************************************************************
 * netTotap_c: Net interface to Tap interface pthread.                    *
 **************************************************************************/
void* netTotap_c(void *input);

/**************************************************************************
 * tapTonet_s: Tap interface to Net interface pthread for server.         *
 **************************************************************************/
void* tapTonet_s(void *input);

/**************************************************************************
 * netTotap_s: Net interface to Tap interface pthread.                    *
 **************************************************************************/
void* netTotap_s(void *input);

/**************************************************************************
 * my_err: prints custom error messages on stderr.                        *
 **************************************************************************/
void my_err(char *msg, ...);

/**************************************************************************
 * usage: prints usage and exits.                                         *
 **************************************************************************/
void usage(void);

/**************************************************************************
 * byteValue: get the byte value with the index pos in the buffer pbuf.   *
 **************************************************************************/
uint8_t byteValue(uint8_t *pbuf, int pos, uint8_t mask);

/**************************************************************************
 * bitValue: get the bit value with the index pos in the buffer pbuf.     *
 **************************************************************************/
uint8_t bitValue(uint8_t *pbuf, int pos);

/**************************************************************************
 * setbitValue: set the bit value with the index pos in the buffer pbuf.  *
 **************************************************************************/
void setbitValue(uint8_t *pbuf, int pos, uint8_t value);

/**************************************************************************
 * addHeader: add packet header to the beginning of the buffer.           *
 **************************************************************************/
void addHeader (char *buff, uint8_t dataType, unsigned short int pkID);

/**************************************************************************
 * getHeader: get packet header from the beginning of the buffer.         *
 **************************************************************************/
struct pkHeader getHeader (char *buff);

/**************************************************************************
 * getDelay: Compute the packet delay using the time stamp from the       *
 *           remote side.                                                        *
 **************************************************************************/
long int getDelay (long int timeStamp);

/**************************************************************************
 * retransmit: Retransmit the data if the ACK is missing (packet lose).   *
 **************************************************************************/
void *retransmit(void *arg);


#endif // UDPTUNNEL_H_INCLUDED
