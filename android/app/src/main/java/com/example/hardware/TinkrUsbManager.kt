package com.example.hardware

import android.content.Context
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import android.util.Log

data class ConnectedUsbDevice(
    val deviceName: String,
    val manufacturer: String?,
    val productName: String?,
    val vendorId: Int,
    val productId: Int,
    val isSupportedMicrocontroller: Boolean
)

class TinkrUsbManager private constructor(private val context: Context) {

    private val usbManager = context.getSystemService(Context.USB_SERVICE) as? UsbManager

    companion object {
        @Volatile
        private var INSTANCE: TinkrUsbManager? = null

        fun getInstance(context: Context): TinkrUsbManager {
            return INSTANCE ?: synchronized(this) {
                val instance = TinkrUsbManager(context.applicationContext)
                INSTANCE = instance
                instance
            }
        }
    }

    /**
     * Lists all physically connected USB Serial/OTG boards using Android native UsbManager
     */
    fun scanConnectedDevices(): List<ConnectedUsbDevice> {
        if (usbManager == null) return emptyList()

        val deviceList = usbManager.deviceList
        val results = mutableListOf<ConnectedUsbDevice>()

        for (device in deviceList.values) {
            val isMCU = isArduinoOrESP32Chipset(device.vendorId, device.productId)
            results.add(
                ConnectedUsbDevice(
                    deviceName = device.deviceName,
                    manufacturer = device.manufacturerName,
                    productName = device.productName ?: "Generic USB-Serial DevKit",
                    vendorId = device.vendorId,
                    productId = device.productId,
                    isSupportedMicrocontroller = isMCU
                )
            )
        }
        return results
    }

    /**
     * Standard USB Vendor IDs for common USB-to-UART bridge chips used in Arduino, ESP32:
     * - CP2102/CP2104: 0x10C4
     * - CH340/CH341 (Clone/Uno): 0x1A86
     * - FTDI FT232R: 0x0403
     * - PL2303: 0x067B
     * - Arduino Uno/Mega: 0x2341 (Official Arduino)
     */
    private fun isArduinoOrESP32Chipset(vendorId: Int, productId: Int): Boolean {
        val supportedVendors = setOf(
            0x10C4, // Silicon Labs (CP210x)
            0x1A86, // Qinheng (CH34x)
            0x0403, // FTDI
            0x067B, // Prolific (PL2303)
            0x2341, // Arduino LLC
            0x1D50  // OpenMoko / custom MCU USB
        )
        return supportedVendors.contains(vendorId)
    }

    fun getChipsetLabel(vendorId: Int): String {
        return when (vendorId) {
            0x10C4 -> "CP210x USB-to-UART Bridge (ESP32 DevKit)"
            0x1A86 -> "CH340/341 USB-Serial Programmer (Arduino/ESP)"
            0x0403 -> "FTDI FT232R Integrated Transceiver"
            0x067B -> "PL2303 Cable-Serial Bridge"
            0x2341 -> "Atmel ATMega Core Controller (Official Arduino)"
            else -> "Generic Serial Controller"
        }
    }
}
