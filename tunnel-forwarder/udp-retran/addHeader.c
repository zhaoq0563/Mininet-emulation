#include "udpTunnel.h"

/**************************************************************************
 * addHeader: add packet header to the beginning of the buffer.           *
 **************************************************************************/

void addHeader(char* buff, uint8_t dataType, unsigned short int pkID){
    struct timeval t;
    gettimeofday(&t,NULL);

    uint8_t *dataTypePointer = (uint8_t*)buff;
    *dataTypePointer = dataType;

    unsigned short int *pkID_pointer = (unsigned short int*)(buff+1);
    *pkID_pointer = pkID;

    long int *timeStampPointer = (long int*)(buff+3);
    *timeStampPointer = 1000000L*(t.tv_sec%1000) + t.tv_usec;
}