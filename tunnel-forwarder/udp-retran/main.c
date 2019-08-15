#include "udpTunnel.h"

int debug;
char *progname;
pthread_t tapTonet_id, netTotap_id;

int main(int argc, char *argv[]) {

  int tap_fd, sock_fd, option;
  int flags = IFF_TUN;
  char if_name[IFNAMSIZ] = "";
  struct sockaddr_in local, cli, ser;
  char server_ip[16] = "";                /* dotted quad IP string */
  char buf[BUFSIZE] = "INITIALIZE ALL TUNNELS!\n";
  char ackbuf[8192] = "";                 /* support packet id range 0:65535 */
  memset(ackbuf, 255, 8192);              /* init all packet id as confirmed: 1 */
  int cliserv = -1;                       /* must be specified on cmd line */

  progname = argv[0];

  /* Check command line options */
  while ((option = getopt(argc, argv, "i:sc:uahd")) > 0) {
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
        strncpy(server_ip, optarg, 15);
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
  }

  /* Initialize tun/tap interface */
  if ((tap_fd = tun_alloc(if_name, flags | IFF_NO_PI)) < 0 ) {
    my_err("Error connecting to tun/tap interface %s!\n", if_name);
    exit(1);
  }

  do_debug("Successfully connected to interface %s\n", if_name);

  if (cliserv == CLIENT) {
    /* Client, try to connect to server */

    /* Init the socket */
    if ((sock_fd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
      perror("socket()");
      exit(1);
    }

    /* Assign the destination address */
    memset(&ser, 0, sizeof(ser));
    ser.sin_family = AF_INET;
    ser.sin_addr.s_addr = inet_addr(server_ip);
    ser.sin_port = htons(PORT);

    /* Send the initialization msg out */
    sendto(sock_fd, buf, BUFSIZE, 0, &ser, sizeof(ser));

    memset(buf, 0, BUFSIZE);

  } else {
    /* Server, wait for connections */

    /* Init the socket */
    if ((sock_fd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
      perror("socket()");
      exit(1);
    }

    /* Bind the socket to local address*/
    memset(&local, 0, sizeof(local));
    local.sin_family = AF_INET;
    local.sin_addr.s_addr = htonl(INADDR_ANY);
    local.sin_port = htons(PORT);
    if (bind(sock_fd, (struct sockaddr*) &local, sizeof(local)) < 0) {
      perror("bind()");
      exit(1);
    }

    /* Retrieve the data and the client address */
    int len = sizeof(cli);
    int count = recvfrom(sock_fd, buf, BUFSIZE, 0, (struct sockaddr *)&cli, &len);
    if (count == -1) {
      perror("recvfrom()");
      exit(1);
    }
    do_debug("Received msg from addr:%s, port:%d\n", inet_ntoa(cli.sin_addr), ntohs(cli.sin_port));

    memset(buf, 0, BUFSIZE);
  }

  struct fds *fd = (struct fds *)malloc(sizeof(struct fds));
  fd->tap        = &tap_fd;
  fd->net        = &sock_fd;
  fd->pAckbuf    = ackbuf;
  fd->servaddr   = &ser;
  fd->clitaddr   = &cli;

  if (cliserv == CLIENT) {
    if (pthread_create(&tapTonet_id, NULL, tapTonet_c, (void *)fd))
    {
      my_err("CLIENT: pthread_create tap to net err\n");
    }
    if (pthread_create(&netTotap_id, NULL, netTotap_c, (void *)fd))
    {
      my_err("CLIENT: pthread_create net to tap err\n");
    }
  } else {
    if (pthread_create(&netTotap_id, NULL, netTotap_s, (void *)fd))
    {
      my_err("SERVER: pthread_create net to tap err\n");
    }
    if (pthread_create(&tapTonet_id, NULL, tapTonet_s, (void *)fd))
    {
      my_err("SERVER: pthread_create tap to net err\n");
    }
  }

  /* block the threads at this point until netTotap exits */
  pthread_join(netTotap_id, NULL);
  do_debug("Write pthread out!\n");

  return(0);
}
