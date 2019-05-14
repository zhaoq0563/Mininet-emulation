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
#define SHAPINGDELAY 1000000 
#define VLEN 1

int debug;
char *progname;
pthread_t tapTonet_id, netTotap_id;

struct fds {
  int *tap;
  int *net;
};

struct thdPar {
  int      *net;
  uint16_t *plength;
  char     *buffer;
  long int *time;
};

const char digits[] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

/**************************************************************************
 * itoc: convert long integer to c string                                 *
 **************************************************************************/
void itoc(long int num, uint16_t *pos, char *buff) {
  buff += (int)*pos;
  for (int i=0;i<8;++i) {
        *buff++ = digits[abs(num % 32)];
        num /= 32;
    }
    *pos += 8;
}

/**************************************************************************
 * ctoi: convert c string to long integer                                 *
 **************************************************************************/
long int ctoi(int pos, char *buff) {
  buff += pos;
  long int a = 0;
  for (int i=0;i<8;++i) {
    a += (isdigit(*buff) ? (*(buff++)-'0') : (*(buff++)-'A'+10)) * pow(32, i);
    }
    return a;
}

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
int cread(int fd, char *buf, int n){
  
  int nread;

  if((nread=read(fd, buf, n)) < 0){
    perror("Reading data");
    exit(1);
  }
  return nread;
}

/**************************************************************************
 * cread: read routine that checks for errors and exits if an error is    *
 *        returned.                                                       *
 **************************************************************************/
int tread(int fd, struct mmsghdr *msgs, unsigned int n, int flags, struct timespec *timeout){
  
  int nread;

  if((nread=recvmmsg(fd, msgs, n, flags, timeout)) < 0){
    perror("Reading data");
    exit(1);
  }
  return nread;
}

/**************************************************************************
 * crecv: "non-blocking" recv routine for continuously receiving data     *
 *        from interfaces.                                                *
 **************************************************************************/
int crecv(int fd, char *buf, int n){
  
  int nrecv;

  /* keep reading the data from the given interface */
  /* enforce returning 0 if no incoming data */
  /* otherwise, return the size of the incoming data */
  nrecv=read(fd, buf, n);
  if (nrecv == -1) return 0;
  else return nrecv;
}

/**************************************************************************
 * cwrite: write routine that checks for errors and exits if an error is  *
 *         returned.                                                      *
 **************************************************************************/
int cwrite(int fd, char *buf, int n){
  
  int nwrite;

  if((nwrite=write(fd, buf, n)) < 0){
    perror("Writing data");
    exit(1);
  }
  return nwrite;
}

/**************************************************************************
 * read_n: ensures we read exactly n bytes, and puts them into "buf".     *
 *         (unless EOF, of course)                                        *
 **************************************************************************/
int read_n(int fd, char *buf, int n) {

  int nread, left = n;

  while(left > 0) {
    if ((nread = cread(fd, buf, left)) == 0){
      return 0 ;      
    }else {
      left -= nread;
      buf += nread;
    }
  }
  return n;  
}

/**************************************************************************
 * sendToTap: send the packet to the tap interface with delay.            *
 **************************************************************************/
void *sendToTap(void *arg) {
  uint16_t nwrite;
  struct thdPar *data = (struct thdPar *)arg;

  /* sleep for delay shaping */
  long int delay = (SHAPINGDELAY - *(data->time));
  printf("thread %d will sleep for %ld usecs!\n", (int)pthread_self(), delay);
  if (delay > 0) usleep(delay);

  do_debug("NET2TAP: Read %d bytes from the network\n", *(data->plength));
  nwrite = cwrite(*(data->net), data->buffer, *(data->plength));
  do_debug("NET2TAP: Written %d bytes to the tap interface\n", nwrite);

  /* free the space */
  free(data->plength);
  free(data->buffer);
  free(data->time);
  free(data);
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
  int       tap_fd = *((struct fds*)input)->tap;
  int       net_fd = *((struct fds*)input)->net;
  uint16_t  nread, nwrite, plength;
  char      buffer[BUFSIZE];

  /* register SIGQUIT signal */
  signal(SIGQUIT,pthread_out);

  while(1)
  {
    /* "non-blocking" read the data from tap interface */
    nread = crecv(tap_fd, buffer, BUFSIZE);

    if (nread != 0) {
      do_debug("TAP2NET: Read %d bytes from the tap interface\n", nread);

      /* send real data + timestamp (16 bytes) to network */
      /* update the buffer */
      struct timeval t;
      gettimeofday(&t, NULL);
      itoc(t.tv_sec, &nread, buffer);
      itoc(t.tv_usec, &nread, buffer);

      /* update the length of the total data */
      plength = htons(nread);

      /* forward the data to tunnel */
      nwrite  = cwrite(net_fd, (char *)&plength, sizeof(plength));
      nwrite  = cwrite(net_fd, buffer, nread);
      do_debug("TAP2NET: Written %d bytes to the network\n", nwrite);
    } else continue;
  }
}

/**************************************************************************
 * tapTonet_s: Tap interface to Net interface pthread for server.         *
 **************************************************************************/
void* tapTonet_s(void* input)
{
  do_debug("tap to net thread is up!\n");
  int       tap_fd = *((struct fds*)input)->tap;
  int       net_fd = *((struct fds*)input)->net;
  uint16_t  nread, nwrite, plength;
  char      buffer[BUFSIZE];

  signal(SIGQUIT, pthread_out);

  while(1)
  {
    nread = cread(tap_fd, buffer, BUFSIZE);

    struct timeval t;
    gettimeofday(&t, NULL);
    itoc(t.tv_sec, &nread, buffer);
    itoc(t.tv_usec, &nread, buffer);
   
    do_debug("TAP2NET: Read %d bytes from the tap interface\n", nread);

    /* write length + packet */
    plength = htons(nread);
    nwrite = cwrite(net_fd, (char *)&plength, sizeof(plength));
    nwrite = cwrite(net_fd, buffer, nread);
    
    do_debug("TAP2NET: Written %d bytes to the network\n", nwrite);
  }
}

/**************************************************************************
 * netTotap_s: Net interface to Tap interface pthread.                      *
 **************************************************************************/
/* thread version */
void* netTotap_s(void* input)
{
  do_debug("net to tap thread is up!\n");

  int      tap_fd = *((struct fds*)input)->tap;
  int      net_fd = *((struct fds*)input)->net;
  uint16_t nread, nwrite, plength;
  struct   timeval time_send, time_receive, time_delay;

  pthread_t tid;
  pthread_attr_t a;
  pthread_attr_init(&a);
  pthread_attr_setdetachstate(&a, PTHREAD_CREATE_DETACHED);

  // FILE *fp_rec = fopen("delay_time_cTos.txt", "w");
  
  /* register SIGPIPE signal */
  signal(SIGPIPE, signal_pipe);

  while(1)
  {
    /* keep reading the data from net interface */
    nread = read_n(net_fd, (char *)&plength, sizeof(plength));
    do_debug("Data length: %d\n", ntohs(plength));

    if (nread == 0) {
       /* ctrl-c at the other end */
      break;
    }

    uint16_t *newplength = (uint16_t *)malloc(sizeof(uint16_t));
    char         *buffer = (char *)malloc(BUFSIZE * sizeof(char));
    long int   *thr_time = (long int *)malloc(sizeof(long int));

    /* read packet */
    nread = read_n(net_fd, buffer, ntohs(plength));

    /* get the send time for the packet */
    time_send.tv_sec  = ctoi(ntohs(plength)-16, buffer);
    time_send.tv_usec = ctoi(ntohs(plength)-8, buffer);

    /* calculate the delay */
    gettimeofday(&time_receive, NULL);
    timersub(&time_receive, &time_send, &time_delay);
    // fprintf(fp_rec, "%ld\n", time_delay.tv_usec);
    // fflush(fp_rec);
    *thr_time = time_delay.tv_usec;

    /* update length of the received data */
    *newplength = ntohs(plength)-16;

    struct thdPar *tp = (struct thdPar *)malloc(sizeof(struct thdPar));
    tp->net     = &tap_fd;
    tp->plength = newplength;
    tp->buffer  = buffer;
    tp->time    = thr_time;

    pthread_create(&tid, &a, sendToTap, (void *)tp);
  }
  // fclose(fp_rec);
}

/**************************************************************************
 * netTotap_c: Net interface to Tap interface pthread.                      *
 **************************************************************************/
/* thread version */
void* netTotap_c(void* input)
{
  do_debug("net to tap thread is up!\n");

  int      tap_fd = *((struct fds*)input)->tap;
  int      net_fd = *((struct fds*)input)->net;
  uint16_t nread, nwrite, plength;
  struct   timeval time_send, time_receive, time_delay;

  pthread_t tid;
  pthread_attr_t a;
  pthread_attr_init(&a);
  pthread_attr_setdetachstate(&a, PTHREAD_CREATE_DETACHED);

  // FILE *fp_rec = fopen("delay_time_sToc.txt", "w");
  
  /* register SIGPIPE signal */
  signal(SIGPIPE, signal_pipe);

  while(1)
  {
    /* keep reading the data from net interface */
    nread = read_n(net_fd, (char *)&plength, sizeof(plength));

    if (nread == 0) {
       /* ctrl-c at the other end */
      break;
    }

    uint16_t *newplength = (uint16_t *)malloc(sizeof(uint16_t));
    char         *buffer = (char *)malloc(BUFSIZE * sizeof(char));
    long int   *thr_time = (long int *)malloc(sizeof(long int));

    /* read packet */
    nread = read_n(net_fd, buffer, ntohs(plength));

    /* get the send time for the packet */
    time_send.tv_sec  = ctoi(ntohs(plength)-16, buffer);
    time_send.tv_usec = ctoi(ntohs(plength)-8, buffer);

    /* calculate the delay */
    gettimeofday(&time_receive, NULL);
    timersub(&time_receive, &time_send, &time_delay);
    // fprintf(fp_rec, "%ld\n", time_delay.tv_usec);
    // fflush(fp_rec);
    *thr_time = time_delay.tv_usec;

    /* update length of the received data */
    *newplength = ntohs(plength)-16;

    struct thdPar *tp = (struct thdPar *)malloc(sizeof(struct thdPar));
    tp->net     = &tap_fd;
    tp->plength = newplength;
    tp->buffer  = buffer;
    tp->time    = thr_time;

    pthread_create(&tid, &a, sendToTap, (void *)tp);
  }
  // fclose(fp_rec);
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
  fprintf(stderr, "-s|-c <serverIP>: run in server mode (-s), or specify server address (-c <serverIP>) (mandatory)\n");
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
  char remote_ip[16] = "";            /* dotted quad IP string */
  unsigned short int port = PORT;
  int sock_fd, net_fd, optval = 1;
  socklen_t remotelen;
  int cliserv = -1;    /* must be specified on cmd line */

  progname = argv[0];
  
  /* Check command line options */
  while ((option = getopt(argc, argv, "i:sc:p:uahd")) > 0) {
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
        break;
      case 'c':
        cliserv = CLIENT;
        strncpy(remote_ip, optarg, 15);
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
  } else if((cliserv == CLIENT)&&(*remote_ip == '\0')) {
    my_err("Must specify server address!\n");
    usage();
  }

  /* initialize tun/tap interface */
  if ((tap_fd = tun_alloc(if_name, flags | IFF_NO_PI)) < 0 ) {
    my_err("Error connecting to tun/tap interface %s!\n", if_name);
    exit(1);
  }

  if (cliserv == CLIENT) {
    /* make the tap_fd non-blocking */
    flags = fcntl(tap_fd, F_GETFL, 0);
    fcntl(tap_fd, F_SETFL, flags | O_NONBLOCK);
  }

  do_debug("Successfully connected to interface %s\n", if_name);

  if ((sock_fd = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
    perror("socket()");
    exit(1);
  }

  int enabled = 1;
  if (setsockopt(sock_fd, SOL_SOCKET, SO_TIMESTAMP, &enabled, sizeof(enabled)) < 0) {
    perror("setsockopt()");
    exit(1);
  } 

  if (cliserv == CLIENT) {
    /* Client, try to connect to server */

    /* assign the destination address */
    memset(&remote, 0, sizeof(remote));
    remote.sin_family = AF_INET;
    remote.sin_addr.s_addr = inet_addr(remote_ip);
    remote.sin_port = htons(port);

    /* connection request */
    if (connect(sock_fd, (struct sockaddr*) &remote, sizeof(remote)) < 0) {
      perror("connect()");
      exit(1);
    }
    net_fd = sock_fd;

    do_debug("CLIENT: Connected to server %s\n", inet_ntoa(remote.sin_addr));
  } else {
    /* Server, wait for connections */

    /* avoid EADDRINUSE error on bind() */
    if (setsockopt(sock_fd, SOL_SOCKET, SO_REUSEADDR, (char *)&optval, sizeof(optval)) < 0) {
      perror("setsockopt()");
      exit(1);
    }
    
    memset(&local, 0, sizeof(local));
    local.sin_family = AF_INET;
    local.sin_addr.s_addr = htonl(INADDR_ANY);
    local.sin_port = htons(port);
    if (bind(sock_fd, (struct sockaddr*) &local, sizeof(local)) < 0) {
      perror("bind()");
      exit(1);
    }
    
    if (listen(sock_fd, 5) < 0) {
      perror("listen()");
      exit(1);
    }
    
    /* wait for connection request */
    remotelen = sizeof(remote);
    memset(&remote, 0, remotelen);
    if ((net_fd = accept(sock_fd, (struct sockaddr*)&remote, &remotelen)) < 0) {
      perror("accept()");
      exit(1);
    }

    do_debug("SERVER: Client connected from %s\n", inet_ntoa(remote.sin_addr));
  }

  struct fds *fd = (struct fds *)malloc(sizeof(struct fds));
  fd->tap = &tap_fd;
  fd->net = &net_fd;

  /* create the tap to net pthread */
  if (cliserv == CLIENT) {
    if (pthread_create(&tapTonet_id, NULL, tapTonet_c, (void *)fd))
    {
      perror("CLIENT: pthread_create tap to net err\n");
    }
    if (pthread_create(&netTotap_id, NULL, netTotap_c, (void *)fd))
    {
      printf("pthread_create net to tap err\n");
    }
  } else {
    if (pthread_create(&tapTonet_id, NULL, tapTonet_s, (void *)fd))
    {
      perror("SERVER: pthread_create tap to net err\n");
    }
    if (pthread_create(&netTotap_id, NULL, netTotap_s, (void *)fd))
    {
      printf("pthread_create net to tap err\n");
    }
  }
  
  /* block the threads at this point until netTotap exits */
  pthread_join(netTotap_id,NULL);
  printf("write pthread out \n");
  
  return(0);
}