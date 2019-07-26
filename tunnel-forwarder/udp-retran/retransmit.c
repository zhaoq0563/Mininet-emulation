#include "udpTunnel.h"

/**************************************************************************
 * retransmit: Retransmit the data if the ACK is missing (packet lose).   *
 **************************************************************************/

void *retransmit(void *arg)
{
	struct retranPar *data = (struct retranPar *)arg;

	int             net_fd = *((struct retranPar *)data)->net;
	struct sockaddr_in *si = ((struct retranPar *)data)->targetAddr;
	char          *pAckbuf = ((struct retranPar *)data)->pAckbuf;
	char           *buffer = ((struct retranPar *)data)->dataBuf;
	uint16_t        *nread = ((struct retranPar *)data)->nread;

    uint16_t nwrite;

	/* sleep for longer than 2*RTT time */
	usleep(RTD);

	if (!bitValue(pAckbuf, getHeader(buffer).pkID)) {
        nwrite = cwrite(net_fd, si, buffer, *nread);
		do_debug("Pkt retransmit: Written %d bytes to the Net interface\n", nwrite);
	}

	/* free the space */
	free(data->nread);
	free(data->dataBuf);
	free(data);
}
