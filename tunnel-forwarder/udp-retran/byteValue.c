#include "udpTunnel.h"

/**************************************************************************
 * byteValue: get the byte value with the index pos in the buffer pbuf.   *
 **************************************************************************/

uint8_t byteValue(uint8_t *pbuf, int pos, uint8_t mask){
    uint8_t result;
    pbuf = pbuf + pos;
    result = *pbuf & mask;
    return result;
}

uint8_t bitValue(uint8_t *pbuf, int pos){
    uint8_t result;
    uint8_t bitpos = pos % 8;
    uint8_t mask = 1<<bitpos;
    pos = (pos-bitpos) / 8;
    result = byteValue(pbuf, pos, mask)
    return result;
}

void setbitValue(uint8_t *pbuf, int pos, uint8_t value){
    uint8_t bitpos = pos % 8;
    uint8_t mask = 1<<bitpos;
    pos = (pos-bitpos) / 8;
    pbuf = pbuf + pos;
    if (value == 0){
        mask = mask ^ 255;
        uint8_t temp = *pbuf & mask;
        *pbuf = temp;
    } else if (value == 1) {
        uint8_t temp = *pbuf | mask;
        *pbuf = temp;
    }
}
