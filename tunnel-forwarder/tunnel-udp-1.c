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


/* buffer for reading from tun/tap interface, must be >= 1500 */
#define BUFSIZE 2000
#define CLIENT 0
#define SERVER 1
#define PORT 55555
#define VLEN 1

int debug;
char *progname;
pthread_t tapTonet_id, netTotap_id;

struct fds {
  int *tap;
  int *net;
  struct sockaddr_in *servaddr;
  struct sockaddr_in *clitaddr;
};

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

/**************************************************************************
 * tun_alloc: allocates or reconnects to a tun/tap device. The caller     *
 *            must reserve enough space in *dev.                          *
 **************************************************************************/
int tun_alloc(char *dev, int flags) {

  struct ifreq ifr;
  int fd, err;
  char *clonedev = "/dev/net/tun";

  if( (fd = open(clonedev , O_RDWR)) < 0 ) {
    perror("Opening /dev/net/tun");
    return fd;
  }

  memset(&ifr, 0, sizeof(ifr));

  ifr.ifr_flags = flags;

  if (*dev) {
    strncpy(ifr.ifr_name, dev, IFNAMSIZ);
  }

  if( (err = ioctl(fd, TUNSETIFF, (void *)&ifr)) < 0 ) {
    perror("ioctl(TUNSETIFF)");
    close(fd);
    return err;
  }

  strcpy(dev, ifr.ifr_name);

  return fd;
}

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

/**************************************************************************
 * tapread: read routine from tap that checks for errors and exits if an  *
 *          error is returned.                                            *
 **************************************************************************/
int tapread(int fd, char *buf, int n){
  
  int nread;

  if((nread=read(fd, buf, n)) < 0){
    perror("Reading data");
    exit(1);
  }
  return nread;
}

/**************************************************************************
 * tapwrite: write routine to tap that checks for errors and exits if an  *
 *           error is returned.                                           *
 **************************************************************************/
int tapwrite(int fd, char *buf, int n){
  
  int nwrite;

  if((nwrite=write(fd, buf, n)) < 0){
    perror("Writing data");
    exit(1);
  }
  return nwrite;
}

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

/**************************************************************************
 * pthread_out: tapTonet exits when receives signal.                      *
 **************************************************************************/
void pthread_out(int signo)
{
  pthread_exit(0);
}

/**************************************************************************
 * tapTonet_c: Tap interface to Net interface pthread for client.         *
 **************************************************************************/
void* tapTonet_c(void* input)
{
  do_debug("tap to net thread is up!\n");
  int             tap_fd = *((struct fds*)input)->tap;
  int             net_fd = *((struct fds*)input)->net;
  struct sockaddr_in *si = ((struct fds*)input)->servaddr;
  uint16_t  nread, nwrite, plength;
  char      buffer[BUFSIZE];

  /* register SIGQUIT signal */
  signal(SIGQUIT,pthread_out);

  while(1)
  {
    /* read the data from tap interface */
    nread = tapread(tap_fd, buffer, BUFSIZE);
    do_debug("TAP2NET: Read %d bytes from the tap interface\n", nread);

    /* forward the data to tunnel */
    nwrite  = cwrite(net_fd, si, buffer, nread);
    do_debug("TAP2NET: Written %d bytes to the network\n", nwrite);
  }
}

/**************************************************************************
 * netTotap_c: Net interface to Tap interface pthread.                      *
 **************************************************************************/
void* netTotap_c(void* input)
{
  do_debug("net to tap thread is up!\n");

  int             tap_fd = *((struct fds*)input)->tap;
  int             net_fd = *((struct fds*)input)->net;
  struct sockaddr_in *si = ((struct fds*)input)->servaddr;
  uint16_t nread, nwrite, plength;
  char     buffer[BUFSIZE];
  
  /* register SIGPIPE signal */
  signal(SIGPIPE,signal_pipe);

  while(1)
  {
    /* read packet */
    nread = cread(net_fd, si, buffer, BUFSIZE);
    do_debug("NET2TAP: Read %d bytes from the network\n", nread);
    /* now buffer[] contains a full packet or frame, write it into the tun/tap interface */
    nwrite = tapwrite(tap_fd, buffer, nread);
    do_debug("NET2TAP: Written %d bytes to the tap interface\n", nwrite);
  }
}

/**************************************************************************
 * tapTonet_s: Tap interface to Net interface pthread for server.         *
 **************************************************************************/
void* tapTonet_s(void* input)
{
  do_debug("tap to net thread is up!\n");
  int             tap_fd = *((struct fds*)input)->tap;
  int             net_fd = *((struct fds*)input)->net;
  struct sockaddr_in *si = ((struct fds*)input)->clitaddr;
  uint16_t  nread, nwrite, plength;
  char      buffer[BUFSIZE];

  /* construct the dummy packet */
  signal(SIGQUIT, pthread_out);

  while(1)
  {
    nread = tapread(tap_fd, buffer, BUFSIZE);
    do_debug("TAP2NET: Read %d bytes from the tap interface\n", nread);

    /* write packet */
    nwrite = cwrite(net_fd, si, buffer, nread);
    do_debug("TAP2NET: Written %d bytes to the network\n", nwrite);
  }
}

/**************************************************************************
 * netTotap_s: Net interface to Tap interface pthread.                      *
 **************************************************************************/
void* netTotap_s(void* input)
{
  do_debug("net to tap thread is up!\n");

  int      tap_fd = *((struct fds*)input)->tap;
  int      net_fd = *((struct fds*)input)->net;
  struct sockaddr_in *si = ((struct fds*)input)->clitaddr;
  uint16_t nread, nwrite, plength;
  char     buffer[BUFSIZE];
  
  /* register SIGPIPE signal */
  signal(SIGPIPE,signal_pipe);

  while(1)
  {
    /* read packet */
    nread = cread(net_fd, si, buffer, BUFSIZE);
    do_debug("NET2TAP: Read %d bytes from the network\n", nread);
    /* now buffer[] contains a full packet or frame, write it into the tun/tap interface */
    nwrite = tapwrite(tap_fd, buffer, nread);
    do_debug("NET2TAP: Written %d bytes to the tap interface\n", nwrite);
  }
}

/**************************************************************************
 * my_err: prints custom error messages on stderr.                        *
 **************************************************************************/
void my_err(char *msg, ...) {

  va_list argp;
  
  va_start(argp, msg);
  vfprintf(stderr, msg, argp);
  va_end(argp);
}

/**************************************************************************
 * usage: prints usage and exits.                                         *
 **************************************************************************/
void usage(void) {
  fprintf(stderr, "Usage:\n");
  fprintf(stderr, "%s -i <ifacename> [-s|-c <serverIP>] [-p <port>] [-u|-a] [-d]\n", progname);
  fprintf(stderr, "%s -h\n", progname);
  fprintf(stderr, "\n");
  fprintf(stderr, "-i <ifacename>: Name of interface to use (mandatory)\n");
  fprintf(stderr, "-s <clientIP>|-c <serverIP>: run in server mode (-s <clientIP>), or specify server address (-c <serverIP>) (mandatory)\n");
  fprintf(stderr, "-p <port>: port to listen on (if run in server mode) or to connect to (in client mode), default 55555\n");
  fprintf(stderr, "-u|-a: use TUN (-u, default) or TAP (-a)\n");
  fprintf(stderr, "-d: outputs debug information while running\n");
  fprintf(stderr, "-h: prints this help text\n");
  exit(1);
}

int main(int argc, char *argv[]) {
  
  int tap_fd, option;
  int flags = IFF_TUN;
  char if_name[IFNAMSIZ] = "";
  struct sockaddr_in local, remote;
  char server_ip[16] = "";            /* dotted quad IP string */
  char client_ip[16] = "";            /* dotted quad IP string */
  unsigned short int port = PORT;
  int sock_fd, net_fd, optval = 1;
  socklen_t remotelen;
  int cliserv = -1;    /* must be specified on cmd line */

  progname = argv[0];
  
  /* Check command line options */
  while ((option = getopt(argc, argv, "i:s:c:p:uahd")) > 0) {
    switch(option) {
      case 'd':
        debug = 1;
        break;
      case 'h':
        usage();
        break;
      case 'i':
        strncpy(if_name, optarg, IFNAMSIZ-1);
        break;
      case 's':
        cliserv = SERVER;
        printf("%s\n", optarg);
        strncpy(client_ip, optarg, 15);
        break;
      case 'c':
        cliserv = CLIENT;
        printf("%s\n", optarg);
        strncpy(server_ip, optarg, 15);
        break;
      case 'p':
        port = atoi(optarg);
        break;
      case 'u':
        flags = IFF_TUN;
        break;
      case 'a':
        flags = IFF_TAP;
        break;
      default:
        my_err("Unknown option %c\n", option);
        usage();
    }
  }

  argv += optind;
  argc -= optind;

  if (argc > 0) {
    my_err("Too many options!\n");
    usage();
  }

  if (*if_name == '\0') {
    my_err("Must specify interface name!\n");
    usage();
  } else if(cliserv < 0) {
    my_err("Must specify client or server mode!\n");
    usage();
  } else if((cliserv == CLIENT)&&(*server_ip == '\0')) {
    my_err("Must specify server address!\n");
    usage();
  } else if((cliserv == SERVER)&&(*client_ip == '\0')) {
    my_err("Must specify client address!\n");
    usage();
  }

  /* initialize tun/tap interface */
  if ((tap_fd = tun_alloc(if_name, flags | IFF_NO_PI)) < 0 ) {
    my_err("Error connecting to tun/tap interface %s!\n", if_name);
    exit(1);
  }

  do_debug("Successfully connected to interface %s\n", if_name);

  if ((sock_fd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
    perror("socket()");
    exit(1);
  }

  if (cliserv == CLIENT) {
    /* Client */

    /* assign the destination address */
    memset(&remote, 0, sizeof(remote));
    remote.sin_family = AF_INET;
    remote.sin_addr.s_addr = inet_addr(server_ip);
    remote.sin_port = htons(port);
  } else {
    /* Server */
    
    memset(&local, 0, sizeof(local));
    local.sin_family = AF_INET;
    local.sin_addr.s_addr = htonl(INADDR_ANY);
    local.sin_port = htons(port);
    if (bind(sock_fd, (struct sockaddr*) &local, sizeof(local)) < 0) {
      perror("bind()");
      exit(1);
    }
  }

  struct fds *fd = (struct fds *)malloc(sizeof(struct fds));
  fd->tap      = &tap_fd;
  fd->net      = &sock_fd;
  fd->servaddr = &remote;
  fd->clitaddr = &local;

  /* create the tap to net pthread */
  if (cliserv == CLIENT) {
    if (pthread_create(&tapTonet_id, NULL, tapTonet_c, (void *)fd))
    {
      perror("CLIENT: pthread_create tap to net err\n");
    }
    if (pthread_create(&netTotap_id, NULL, netTotap_c, (void *)fd))
    {
      printf("CLIENT: pthread_create net to tap err\n");
    }
  } else {
    if (pthread_create(&tapTonet_id, NULL, tapTonet_s, (void *)fd))
    {
      perror("SERVER: pthread_create tap to net err\n");
    }
    if (pthread_create(&netTotap_id, NULL, netTotap_s, (void *)fd))
    {
      printf("SERVER: pthread_create net to tap err\n");
    }
  }
  
  /* block the threads at this point until netTotap exits */
  pthread_join(netTotap_id,NULL);
  printf("write pthread out \n");
  
  return(0);
}