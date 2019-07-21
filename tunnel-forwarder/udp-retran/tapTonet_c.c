#include "udpTunnel.h"

/**************************************************************************
 * tapTonet_c: Tap interface to Net interface pthread for client.         *
 **************************************************************************/

void* tapTonet_c(void *input)
{
    do_debug("Tap to Net thread is up!\n");

    int             tap_fd = *((struct fds*)input)->tap;
    int             net_fd = *((struct fds*)input)->net;
    struct sockaddr_in *si = ((struct fds*)input)->servaddr;
    char          *pAckbuf = ((struct fds*)input)->pAckbuf;

    uint16_t  nwrite, plength;
    unsigned short int curpktID = 0;                      /* initialize packet id as 0 */

    pthread_t tid;
    pthread_attr_t a;
    pthread_attr_init(&a);
    pthread_attr_setdetachstate(&a, PTHREAD_CREATE_DETACHED);

    /* register SIGQUIT signal */
    signal(SIGQUIT, pthread_out);

    while(1)
    {
        char    *buffer = (char *)malloc(BUFSIZE * sizeof(char));
        uint16_t *nread = (uint16_t *)malloc(sizeof(uint16_t));

        /* read the data from tap interface */
        *nread = tapread(tap_fd, buffer+HEADERSIZE, BUFSIZE-HEADERSIZE);
        do_debug("TAP2NET: Read %d bytes from the tap interface\n", *nread);

        /* add the 11 bytes packet header at the beginning of the buffer*/
        uint8_t dataType = 1;
        unsigned short int pkID = 0;
        uint8_t ackCntcheck = 0;

        while(1)
        {
            if (curpktID > 65535) {
                curpktID = 0;   
            }
            uint8_t ackflag = bitValue(pAckbuf, curpktID);
            if (ackflag) {
                setbitValue(pAckbuf, curpktID, 0);           /* set packet id as unconfirmed */
                pkID = curpktID++;
                break;
            } else {
                curpktID++;
                ackCntcheck++;
            }

            if (ackCntcheck > 5) {
                // warning: cannot find acked pkID indiciating not enough packet id     
            }
        }

        addHeader(buffer, dataType, pkID);
        *nread = *nread + HEADERSIZE;

        /* forward the data to tunnel */
        nwrite = cwrite(net_fd, si, buffer, *nread);
        do_debug("TAP2NET: Written %d bytes to the network\n", nwrite);

        struct retranPar *retran = (struct retranPar *)malloc(sizeof(struct retranPar));
        retran->net        = &net_fd;
        retran->pAckbuf    = pAckbuf;
        retran->dataBuf    = buffer;
        retran->targetAddr = si;
        retran->nread      = nread;

        pthread_create(&tid, &a, retransmit, (void *)retran);
    }
}
