import spidev
import time

spi = spidev.SpiDev()
spi.open(0,0)


def readadc(adcnum):
# read SPI data from MCP3004 chip, 4 possible adc's (0 thru 3)
    if adcnum >3 or adcnum <0:
       return-1
    r = spi.xfer2([1,8+adcnum <<4,0])
    adcout = ((r[1] &3) <<8)+r[2]
    return adcout
