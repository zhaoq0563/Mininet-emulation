#include "udpTunnel.h"

/**************************************************************************
 * getDelay: Compute the packet delay using the time stamp from the       *
 *           remote side.                                                 *
 **************************************************************************/

long int getDelay (long int timeStamp){
    struct timeval time_receive;
    gettimeofday(&time_receive, NULL);
    long int t_rec = 1000000L * (time_receive.tv_sec%1000) + time_receive.tv_usec;
    long int delay = t_rec-timeStamp;

    //Dealing with the case across 999999999.
    if (delay < -500000000L) {
        delay = delay + 1000000000L;
    }

    return delay;
}
