#include "udpTunnel.h"

/**************************************************************************
 * retransmit: Retransmit the data if the ACK is missing (packet lose).   *
 **************************************************************************/

void *retransmit(void *arg)
{
	int             net_fd = *((struct fds*)arg)->net;
	struct sockaddr_in *si = ((struct fds*)arg)->targetAddr;
	char          *pAckbuf = ((struct fds*)arg)->pAckbuf;
	char           *buffer = ((struct fds*)arg)->dataBuf;
	uint16_t        *nread = ((struct fds*)arg)->nread;

    uint16_t nwrite;

	/* sleep for longer than 2*RTT time */
	usleep(RTD);

	if (!bitValue(pAckbuf, getHeader(buffer).pkID)) {
        nwrite = cwrite(net_fd, si, buffer, nread);
		do_debug("Pkt retransmit: Written %d bytes to the Net interface\n", nwrite);
	}

	/* free the space */
	free(arg->nread);
	free(arg->buffer);
	free(arg);
}
