#include "udpTunnel.h"

/**************************************************************************
 * getHeader: get packet header from the beginning of the buffer.         *
 **************************************************************************/

struct pkHeader getHeader(char* buff){
    struct pkHeader h;

    uint8_t* dataTypePointer = (uint8_t*)buff;
    h.dataType = *dataTypePointer;

    unsigned short int *pkID_pointer = (unsigned short int*)(buff+1);
    h.pkID = *pkID_pointer;

    long int *timeStampPointer = (long int*)(buff+3);
    h.timeStamp = *timeStampPointer;

    return h;
}