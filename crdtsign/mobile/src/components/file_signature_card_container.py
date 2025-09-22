import flet as ft
from .file_signature_card import FileSignature, FileSignatureCard
from datetime import datetime
import time

from utils.storage import file_storage

class FileSignatureCardContainer(ft.Column):
    def __init__(self, page: ft.Page):
        """Container for file signature cards"""
        super().__init__()
        self.page = page
        self.cards = ft.Column()
        self.placeholder = ft.Container(
            content=ft.Text("No file signatures found."),
            alignment=ft.alignment.center,
            expand=True,
            height=100,
        )
        self.scroll = ft.ScrollMode.AUTO
        self.expand = True
        self.controls = [
            self.placeholder,
            self.cards,
        ]

        # Initially show placeholder since no cards
        self.placeholder.visible = True

    def add_card(self, new_file_signature: FileSignature, update_page=True):
        new_card = FileSignatureCard(new_file_signature, self.card_delete)
        self.cards.controls.append(new_card.card)
        # Update placeholder visibility based on current cards count
        self.placeholder.visible = len(self.cards.controls) == 0
        if update_page:
            self.page.update()

    def card_delete(self, card_instance):
        self.cards.controls.remove(card_instance.card)
        # Update placeholder visibility based on current cards count
        self.placeholder.visible = len(self.cards.controls) == 0
        self.page.update()

    def update_container(self):
        time.sleep(0.1)
        signatures = file_storage.get_signatures()
        self.cards.controls = []
        for signature in signatures:
            file_signature = FileSignature(
                file_id=signature["id"],
                file_name=signature["name"],
                file_hash=signature["hash"],
                signature=signature["signature"] if isinstance(signature["signature"], str) else signature["signature"].hex(),
                signed_by=signature["username"],
                signed_id=signature["user_id"],
                signed_at=datetime.fromisoformat(signature["signed_on"]).astimezone(datetime.now().tzinfo),
                expiration_date=datetime.fromisoformat(signature["expiration_date"]).astimezone(datetime.now().tzinfo) if "expiration_date" in signature and signature["expiration_date"] else None,
                data_retention_exp_date=datetime.fromisoformat(signature["data_retention_new_exp_date"]).astimezone(datetime.now().tzinfo) if "data_retention_new_exp_date" in signature and signature["data_retention_new_exp_date"] else None,
            )
            self.add_card(file_signature, update_page=False)

        # Update placeholder visibility after rebuilding all cards
        self.placeholder.visible = len(self.cards.controls) == 0
        self.page.update()