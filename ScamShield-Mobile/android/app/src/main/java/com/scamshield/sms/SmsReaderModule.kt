package com.scamshield.sms

import android.content.ContentValues.TAG
import android.provider.Telephony
import android.util.Log
import com.facebook.react.bridge.*

class SmsReaderModule(reactContext: ReactApplicationContext) : ReactContextBaseJavaModule(reactContext) {

    override fun getName(): String = "SmsReaderModule"

    @ReactMethod
    fun readSms(maxCount: Int, promise: Promise) {
        try {
            val cursor = reactApplicationContext.contentResolver.query(
                Telephony.Sms.Inbox.CONTENT_URI,
                arrayOf("_id", "address", "body", "date", "read"),
                null, null,
                "date DESC"
            ) ?: run {
                promise.resolve(Arguments.createArray())
                return
            }

            val messages = Arguments.createArray()
            var count = 0
            while (cursor.moveToNext() && count < maxCount) {
                val msg = Arguments.createMap()
                msg.putString("_id", cursor.getString(0))
                msg.putString("address", cursor.getString(1) ?: "Unknown")
                msg.putString("body", cursor.getString(2) ?: "")
                msg.putString("date", cursor.getString(3))
                msg.putInt("read", cursor.getInt(4))
                messages.pushMap(msg)
                count++
            }
            cursor.close()
            promise.resolve(messages)
        } catch (e: Exception) {
            Log.e(TAG, "SmsReaderModule error", e)
            promise.reject("SMS_READ_ERROR", e.message)
        }
    }
}
