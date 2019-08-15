#include "udpTunnel.h"

/**************************************************************************
 * sendToTap: send the packet to the tap interface with delay.            *
 **************************************************************************/

void *sendToTap(void *arg)
{
  uint16_t nwrite;
  struct thdPar *data = (struct thdPar *)arg;

  /* sleep for delay shaping */
  long int delay = (SHAPINGDELAY - *(data->time));
  if (delay > 0) {
  	// do_debug("thread %d will sleep for %ld usecs!\n", (int)pthread_self(), delay);
  	usleep(delay);
  }

  nwrite = tapwrite(*(data->net), data->buffer, *(data->plength));
  // do_debug("NET2TAP-thread: Written %d bytes to the tap interface\n", nwrite);

  /* free the space */
  free(data->plength);
  free(data->buffer-HEADERSIZE);
  free(data->time);
  free(data);
}
