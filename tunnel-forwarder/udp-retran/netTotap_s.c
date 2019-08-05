#include "udpTunnel.h"

/**************************************************************************
 * netTotap_s: Net interface to Tap interface pthread.                    *
 **************************************************************************/

void* netTotap_s(void *input)
{
    do_debug("Net to Tap thread is up!\n");

    int             tap_fd = *((struct fds *)input)->tap;
    int             net_fd = *((struct fds *)input)->net;
    struct sockaddr_in *si = ((struct fds *)input)->clitaddr;
    char          *pAckbuf = ((struct fds *)input)->pAckbuf;

    uint16_t nread, nwrite;
    char     buffer[BUFSIZE];

    char AckIDbuffer_1[1000];                   /* hold 500 ack id */
    char AckIDbuffer_2[1000];                   /* hold 500 ack id */
    char AckIDbuffer_3[1000];                   /* hold 500 ack id */
    int AckIDCnt[3] = {0};

    uint8_t curAckIDbuf = 1;
    uint8_t AckInt_ms = 100;                    /* send Ack packet back every AckInt_ms */
    char bufferAckReturn[3011];                 /* buffer for sending Ack packets */

    struct timeval time_receive;
    gettimeofday(&time_receive, NULL);
    long int timeStamp_prevSent = 1000000L * (time_receive.tv_sec) + time_receive.tv_usec;

    pthread_t tid;
    pthread_attr_t a;
    pthread_attr_init(&a);
    pthread_attr_setdetachstate(&a, PTHREAD_CREATE_DETACHED);

    /* register SIGPIPE signal */
    signal(SIGPIPE, signal_pipe);

    while(1)
    {
        /* read packet */
        nread = cread(net_fd, si, buffer, BUFSIZE);
        do_debug("NET2TAP: Read %d bytes from the network\n", nread);

        /* get the header from the packet */
        struct pkHeader h = getHeader(buffer);

        if (h.dataType == 1) {                                      /* only data packet with type 1 */
            /* record the received pkt */
            if (curAckIDbuf == 1) {
                if (AckIDCnt[0] > 500) {
                    do_debug("NET2TAP ACK: Current ack buffer is not enough\n");
                } else {
                    unsigned short int *pkID_pointer = (unsigned short int*)(AckIDbuffer_1+AckIDCnt[0]*2);
                    *pkID_pointer = h.pkID;
                    AckIDCnt[0]++;
                }
            } else if (curAckIDbuf == 2) {
                if(AckIDCnt[1] > 500){
                    do_debug("NET2TAP ACK: Current ack buffer is not enough\n");
                } else {
                    unsigned short int *pkID_pointer = (unsigned short int*)(AckIDbuffer_2+AckIDCnt[1]*2);
                    *pkID_pointer = h.pkID;
                    AckIDCnt[1]++;
                }
            } else if (curAckIDbuf == 3) {
                if(AckIDCnt[2]>500){
                    do_debug("NET2TAP ACK: Current ack buffer is not enough\n");
                } else {
                    unsigned short int *pkID_pointer = (unsigned short int*)(AckIDbuffer_3+AckIDCnt[2]*2);
                    *pkID_pointer = h.pkID;
                    AckIDCnt[2]++;
                }
            }

            /* decide whether acks need to be sent */
            gettimeofday(&time_receive, NULL);
            long int curTimestamp = 1000000L * (time_receive.tv_sec) + time_receive.tv_usec;   
            long int timegap = curTimestamp - timeStamp_prevSent;
            if (timegap/1000 > AckInt_ms && (AckIDCnt[0]+AckIDCnt[1]+AckIDCnt[2]) != 0){
                uint8_t dataType = 2;                               /* ack package data type 2 */
                unsigned short int pkID = 0;                        /* for ack package paceket id does not matter */
                uint16_t acksize = AckIDCnt[0] + AckIDCnt[1] + AckIDCnt[2];
                /* memory copy 3 ack buffers to ack return buffer */
                memcpy(bufferAckReturn+HEADERSIZE, AckIDbuffer_1, AckIDCnt[0]*sizeof(char)*2);
                memcpy(bufferAckReturn+HEADERSIZE+AckIDCnt[0]*sizeof(char)*2, AckIDbuffer_2, AckIDCnt[1]*sizeof(char)*2);
                memcpy(bufferAckReturn+HEADERSIZE+AckIDCnt[0]*sizeof(char)*2+AckIDCnt[1]*sizeof(char)*2, AckIDbuffer_3, AckIDCnt[2]*sizeof(char)*2);

                addHeader(bufferAckReturn, dataType, pkID);
                acksize = acksize*sizeof(char)*2 + HEADERSIZE;

                /* send bufferAckReturn, acksize back */
                nwrite = cwrite(net_fd, si, bufferAckReturn, acksize);
                do_debug("NET2TAP ACK: %d bytes acks sent\n", nwrite);

                /* update current AckIDbuffer */
                curAckIDbuf = ++curAckIDbuf > 3 ? 1 : curAckIDbuf;

                /* reset AckIDbuff and timer for sending acks */
                AckIDCnt[curAckIDbuf-1] = 0;  
                timeStamp_prevSent = curTimestamp;
            }

            nwrite = tapwrite(tap_fd, buffer+HEADERSIZE, nread-HEADERSIZE);
            do_debug("NET2TAP: Write %d bytes to the tap\n", nwrite);

        } else if (h.dataType == 2) {                               /* ack package */
            uint16_t ackCnt = (nread - HEADERSIZE) / 2;
            do_debug("NET2TAP ACK: %d acks received from the client\n", ackCnt);

            for (int i=0; i<ackCnt; ++i) {
                unsigned short int *pkID_pointer = (unsigned short int*)(buffer + HEADERSIZE + 2*i);
                unsigned short int pkID = *pkID_pointer;
                setbitValue(pAckbuf, pkID, 1);                      /* Ack packet with pkID */
            }
        }
    }
}
