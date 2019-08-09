#include "udpTunnel.h"

/**************************************************************************
 * getDelay: Compute the packet delay using the time stamp from the       *
 *           remote side.                                                 *
 **************************************************************************/

long int getDelay (long int timeStamp){
    struct timeval time_receive;
    gettimeofday(&time_receive, NULL);
    long int t_rec = 1000000L * (time_receive.tv_sec%10000) + time_receive.tv_usec;
    long int delay = t_rec-timeStamp;

    /* Dealing with the case across 9999999999 */
    if (delay < -5000000000L) {
        delay = delay + 10000000000L;
    }

    if (delay < 0L){
        delay = 0L;
    }

    return delay;
}
