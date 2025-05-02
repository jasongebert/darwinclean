
from fastapi import FastAPI, Request
from pydantic import BaseModel
from playwright.async_api import async_playwright
import uvicorn
import asyncio

app = FastAPI()

class BookingRequest(BaseModel):
    full_name: str
    email: str
    phone: str
    address: str = "6 Granites Dr, Rosebery NT 0830"
    confirm_booking: bool = False
    preferred_date: str = None  # Optional: "Tuesday, May 6, 10:00 AM"

BOOKING_URL = "https://book.servicem8.com/request_service_online_booking?strVendorUUID=d10616d6-3524-4cfb-9227-2c061f9912ab&utm_source=Website#0b98324a-e6f8-436c-ae4b-01aa47c3d71b"

async def extract_time_slots(page):
    await page.wait_for_selector(".webflow-booking-schedule-button-v3")
    slots = await page.locator(".webflow-booking-schedule-button-v3").all_text_contents()
    return [s.replace("\n", " ").strip() for s in slots if s.strip()]

async def perform_booking(data: BookingRequest):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(BOOKING_URL)

        # Step 1: Click "Deluxe Clean"
        await page.wait_for_selector(".webflow-booking-services-button-v3")
        await page.locator(".webflow-booking-services-button-v3:text('Deluxe Clean')").click()

        # Step 2: Fill contact details
        await page.wait_for_selector("#strContactName")
        await page.fill("#strContactName", data.full_name)
        await page.fill("#strEmail", data.email)
        await page.fill("#strPhoneNumber", data.phone)
        await page.fill("#strJobAddress", data.address)

        # Click Next to go to time selection
        await page.click("#NextButton")

        # Step 3: Extract time slots
        slots = await extract_time_slots(page)

        if not data.confirm_booking or not data.preferred_date:
            await browser.close()
            return {"next_available": slots[0] if slots else None, "other_days_with_slots": slots[1:5]}

        # Step 4: Select preferred slot and confirm
        for slot in await page.locator(".webflow-booking-schedule-button-v3").all():
            text = await slot.text_content()
            if data.preferred_date.lower() in text.lower():
                await slot.click()
                break

        await page.click(".webflow-booking-proceed-button-v3:text('Review')")
        await page.click(".webflow-booking-proceed-button-v3:text('PAY')")
        await browser.close()

        return {"status": "Booking confirmed for " + data.preferred_date}

@app.post("/book")
async def book_job(req: BookingRequest):
    result = await perform_booking(req)
    return result
