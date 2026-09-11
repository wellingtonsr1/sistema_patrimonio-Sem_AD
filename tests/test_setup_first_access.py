"""Testes do primeiro acesso (/setup): exclusividade e liberação da reivindicação."""

from app.models.user import User


def test_segunda_reivindicacao_de_primeiro_acesso_falha(db_session):
    from app.web.routes import _claim_first_access

    assert _claim_first_access(db_session) is True
    db_session.commit()

    # Nova sessão, mesmo engine de teste: a chave primária do singleton
    # impede uma segunda reivindicação.
    from sqlalchemy.orm import sessionmaker

    outra = sessionmaker(bind=db_session.get_bind())()
    try:
        assert _claim_first_access(outra) is False
    finally:
        outra.close()


def test_setup_cria_um_unico_admin_e_desabilita_o_fluxo(unauth_client, db_session):
    assert unauth_client.get("/setup").status_code == 200

    primeiro = unauth_client.post(
        "/setup",
        data={
            "full_name": "Admin Um",
            "username": "admin1",
            "password": "senha-forte-1",
            "confirm_password": "senha-forte-1",
            "email": "admin1@empresa.local",
        },
        follow_redirects=False,
    )
    assert primeiro.status_code == 303
    assert primeiro.headers["location"] == "/login"

    # Depois do primeiro acesso, o fluxo fica desabilitado
    assert unauth_client.get("/setup", follow_redirects=False).status_code == 303

    segunda = unauth_client.post(
        "/setup",
        data={
            "full_name": "Admin Dois",
            "username": "admin2",
            "password": "senha-forte-2",
            "confirm_password": "senha-forte-2",
        },
        follow_redirects=False,
    )
    assert segunda.status_code == 303
    assert segunda.headers["location"] == "/login"

    usuarios = db_session.query(User).all()
    assert [u.username for u in usuarios] == ["admin1"]
    assert usuarios[0].is_admin is True


def test_validacao_nao_consome_o_primeiro_acesso(unauth_client):
    resp = unauth_client.post(
        "/setup",
        data={
            "full_name": "Admin",
            "username": "admin",
            "password": "curta",
            "confirm_password": "curta",
        },
    )
    assert resp.status_code == 200
    assert "no mínimo 8 caracteres" in resp.text

    # Continua disponível para uma tentativa correta
    assert unauth_client.get("/setup", follow_redirects=False).status_code == 200
