from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, auth, bookings, claims, destinations, experiences, lodge_admin, lodges, reviews, search, species, uploads, users, webhooks


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(lodges.router)
api_router.include_router(experiences.router)
api_router.include_router(bookings.router)
api_router.include_router(reviews.router)
api_router.include_router(users.router)
api_router.include_router(lodge_admin.router)
api_router.include_router(admin.router)
api_router.include_router(search.router)
api_router.include_router(species.router)
api_router.include_router(destinations.router)
api_router.include_router(claims.router)
api_router.include_router(uploads.router)
api_router.include_router(webhooks.router)
