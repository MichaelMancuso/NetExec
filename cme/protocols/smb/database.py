#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging


class database:

    def __init__(self, conn, metadata=None):
        # this is still named "conn" when it is the Session object, TODO: rename
        self.conn = conn
        self.metadata = metadata
        self.computers_table = metadata.tables["computers"]

        self.users_table = metadata.tables["users"]
        self.groups_table = metadata.tables["groups"]
        self.shares_table = metadata.tables["shares"]

    @staticmethod
    def db_schema(db_conn):
        db_conn.execute('''CREATE TABLE "computers" (
            "id" integer PRIMARY KEY,
            "ip" text,
            "hostname" text,
            "domain" text,
            "os" text,
            "dc" boolean,
            "smbv1" boolean,
            "signing" boolean,
            "spooler" boolean,
            "zerologon" boolean,
            "petitpotam" boolean
            )''')

        # type = hash, plaintext
        db_conn.execute('''CREATE TABLE "users" (
            "id" integer PRIMARY KEY,
            "domain" text,
            "username" text,
            "password" text,
            "credtype" text,
            "pillaged_from_computerid" integer,
            FOREIGN KEY(pillaged_from_computerid) REFERENCES computers(id)
            )''')

        db_conn.execute('''CREATE TABLE "groups" (
            "id" integer PRIMARY KEY,
            "domain" text,
            "name" text
            )''')

        # This table keeps track of which credential has admin access over which machine and vice-versa
        db_conn.execute('''CREATE TABLE "admin_relations" (
            "id" integer PRIMARY KEY,
            "userid" integer,
            "computerid" integer,
            FOREIGN KEY(userid) REFERENCES users(id),
            FOREIGN KEY(computerid) REFERENCES computers(id)
            )''')

        db_conn.execute('''CREATE TABLE "loggedin_relations" (
            "id" integer PRIMARY KEY,
            "userid" integer,
            "computerid" integer,
            FOREIGN KEY(userid) REFERENCES users(id),
            FOREIGN KEY(computerid) REFERENCES computers(id)
            )''')

        db_conn.execute('''CREATE TABLE "group_relations" (
            "id" integer PRIMARY KEY,
            "userid" integer,
            "groupid" integer,
            FOREIGN KEY(userid) REFERENCES users(id),
            FOREIGN KEY(groupid) REFERENCES groups(id)
            )''')

        db_conn.execute('''CREATE TABLE "shares" (
            "id" integer PRIMARY KEY,
            "computerid" text,
            "userid" integer,
            "name" text,
            "remark" text,
            "read" boolean,
            "write" boolean,
            FOREIGN KEY(userid) REFERENCES users(id)
            UNIQUE(computerid, userid, name)
        )''')

        #db_conn.execute('''CREATE TABLE "ntds_dumps" (
        #    "id" integer PRIMARY KEY,
        #    "computerid", integer,
        #    "domain" text,
        #    "username" text,
        #    "hash" text,
        #    FOREIGN KEY(computerid) REFERENCES computers(id)
        #    )''')

    def add_share(self, computerid, userid, name, remark, read, write):
        self.conn.execute("INSERT OR IGNORE INTO shares (computerid, userid, name, remark, read, write) VALUES (?,?,?,?,?,?)", [computerid, userid, name, remark, read, write])
        self.conn.close()

    def is_share_valid(self, shareID):
        """
        Check if this share ID is valid.
        """
        self.conn.execute('SELECT * FROM shares WHERE id=? LIMIT 1', [shareID])
        results = self.conn.fetchall()
        self.conn.close()

        logging.debug(f"is_share_valid(shareID={shareID}) => {len(results) > 0}")
        return len(results) > 0

    def get_shares(self, filterTerm = None):
        if self.is_share_valid(filterTerm):
            self.conn.execute("SELECT * FROM shares WHERE id=?", [filterTerm])
        elif filterTerm:
            self.conn.execute("SELECT * FROM shares WHERE LOWER(name) LIKE LOWER(?)", [f"%{filterTerm}%"])
        else:
            self.conn.execute("SELECT * FROM shares")

        results = self.conn.fetchall()
        return results

    def get_shares_by_access(self, permissions, shareID=None):
        permissions = permissions.lower()

        if shareID:
            if permissions == "r":
                self.conn.execute("SELECT * FROM shares WHERE id=? AND read=1",[shareID])
            elif permissions == "w":
                self.conn.execute("SELECT * FROM shares WHERE id=? write=1", [shareID])
            elif permissions == "rw":
                self.conn.execute("SELECT * FROM shares WHERE id=? AND read=1 AND write=1", [shareID])
        else:
            if permissions == "r":
                self.conn.execute("SELECT * FROM shares WHERE read=1")
            elif permissions == "w":
                self.conn.execute("SELECT * FROM shares WHERE write=1")
            elif permissions == "rw":
                self.conn.execute("SELECT * FROM shares WHERE read= AND write=1")

        results = self.conn.fetchall()
        return results

    def get_users_with_share_access(self, computerID, share_name, permissions):
        permissions = permissions.lower()

        if permissions == "r":
            self.conn.execute("SELECT userid FROM shares WHERE computerid=(?) AND name=(?) AND read=1", [computerID, share_name])
        elif permissions == "w":
            self.conn.execute("SELECT userid FROM shares WHERE computerid=(?) AND name=(?) AND write=1", [computerID, share_name])
        elif permissions == "rw":
            self.conn.execute("SELECT userid FROM shares WHERE computerid=(?) AND name=(?) AND read=1 AND write=1", [computerID, share_name])

        results = self.conn.fetchall()
        return results

    #pull/545
    def add_computer(self, ip, hostname, domain, os, smbv1, signing=None, spooler=0, zerologon=0, petitpotam=0, dc=None):
        """
        Check if this host has already been added to the database, if not add it in.
        """
        domain = domain.split('.')[0].upper()
        sess = self.conn

        results = sess.query(self.computers_table).filter(self.computers_table.c.ip == ip).all()
        host = {
            "ip": ip,
            "hostname": hostname,
            "domain": domain,
            "os": os,
            "dc": dc,
            "smbv1": smbv1,
            "signing": signing,
            "spooler": spooler,
            "zerologon": zerologon,
            "petitpotam": petitpotam
        }
        print(f"RESULTS: {results}")
        print(f"IP: {ip}")
        print(f"Hostname: {hostname}")
        print(f"Domain: {domain}")
        print(f"OS: {os}")
        print(f"SMB: {smbv1}")
        print(f"Signing: {signing}")
        print(f"DC: {dc}")

        if not results:
            # host doesn't exist in the DB
            pass

        if not len(results):
            try:
                sess.execute("INSERT INTO computers (ip, hostname, domain, os, dc, smbv1, signing) VALUES (?,?,?,?,?,?,?,?,?,?)", [ip, hostname, domain, os, dc, smbv1, signing, spooler, zerologon, petitpotam])
            except Exception as e:
                print(f"Exception: {e}")
                sess.execute("INSERT INTO computers (ip, hostname, domain, os, dc) VALUES (?,?,?,?,?)", [ip, hostname, domain, os, dc])
        else:
            for host in results:
                try:
                    if (hostname != host[2]) or (domain != host[3]) or (os != host[4]) or (smbv1 != host[6]) or (signing != host[7]):
                        sess.execute("UPDATE computers SET hostname=?, domain=?, os=?, smbv1=?, signing=?, spooler=?, zerologon=?, petitpotam=? WHERE id=?", [hostname, domain, os, smbv1, signing, spooler, zerologon, petitpotam, host[0]])
                except:
                    if (hostname != host[2]) or (domain != host[3]) or (os != host[4]):
                        sess.execute("UPDATE computers SET hostname=?, domain=?, os=? WHERE id=?", [hostname, domain, os, host[0]])
                if dc != None and (dc != host[5]):
                    sess.execute("UPDATE computers SET dc=? WHERE id=?", [dc, host[0]])
        sess.execute('''SELECT * from computers''')
        res2 = sess.fetchall()
        print(f"inside res: {res2}")
        self.conn.commit()
        sess.close()

        return sess.lastrowid

    def update_computer(self, host_id, hostname=None, domain=None, os=None, smbv1=None, signing=None, spooler=None, zerologon=None, petitpotam=None, dc=None):
        data = {
            "id": host_id,
            "spooler": spooler
        }
        # Computers.Update(data)
        # self.conn.execute(Computers.Update(data))

    def add_credential(self, credtype, domain, username, password, groupid=None, pillaged_from=None):
        """
        Check if this credential has already been added to the database, if not add it in.
        """
        domain = domain.split('.')[0].upper()
        user_rowid = None

        if groupid and not self.is_group_valid(groupid):
            self.conn.close()
            return

        if pillaged_from and not self.is_computer_valid(pillaged_from):
            self.conn.close()
            return

        self.conn.execute("SELECT * FROM users WHERE LOWER(domain)=LOWER(?) AND LOWER(username)=LOWER(?) AND LOWER(credtype)=LOWER(?)", [domain, username, credtype])
        results = self.conn.fetchall()

        if not len(results):
            self.conn.execute("INSERT INTO users (domain, username, password, credtype, pillaged_from_computerid) VALUES (?,?,?,?,?)", [domain, username, password, credtype, pillaged_from])
            user_rowid = self.conn.lastrowid
            if groupid:
                self.conn.execute("INSERT INTO group_relations (userid, groupid) VALUES (?,?)", [user_rowid, groupid])
        else:
            for user in results:
                if not user[3] and not user[4] and not user[5]:
                    self.conn.execute('UPDATE users SET password=?, credtype=?, pillaged_from_computerid=? WHERE id=?', [password, credtype, pillaged_from, user[0]])
                    user_rowid = self.conn.lastrowid
                    if groupid and not len(self.get_group_relations(user_rowid, groupid)):
                        self.conn.execute("INSERT INTO group_relations (userid, groupid) VALUES (?,?)", [user_rowid, groupid])

        self.conn.close()

        logging.debug('add_credential(credtype={}, domain={}, username={}, password={}, groupid={}, pillaged_from={}) => {}'.format(credtype, domain, username, password, groupid, pillaged_from, user_rowid))

        return user_rowid

    def add_user(self, domain, username, groupid=None):
        if groupid and not self.is_group_valid(groupid):
            return

        domain = domain.split('.')[0].upper()
        user_rowid = None

        self.conn.execute("SELECT * FROM users WHERE LOWER(domain)=LOWER(?) AND LOWER(username)=LOWER(?)", [domain, username])
        results = self.conn.fetchall()

        if not len(results):
            self.conn.execute("INSERT INTO users (domain, username, password, credtype, pillaged_from_computerid) VALUES (?,?,?,?,?)", [domain, username, '', '', ''])
            user_rowid = self.conn.lastrowid
            if groupid:
                self.conn.execute("INSERT INTO group_relations (userid, groupid) VALUES (?,?)", [user_rowid, groupid])
        else:
            for user in results:
                if (domain != user[1]) and (username != user[2]):
                    self.conn.execute("UPDATE users SET domain=?, user=? WHERE id=?", [domain, username, user[0]])
                    user_rowid = self.conn.lastrowid

                if not user_rowid: user_rowid = user[0]
                if groupid and not len(self.get_group_relations(user_rowid, groupid)):
                    self.conn.execute("INSERT INTO group_relations (userid, groupid) VALUES (?,?)", [user_rowid, groupid])

        self.conn.close()

        logging.debug('add_user(domain={}, username={}, groupid={}) => {}'.format(domain, username, groupid, user_rowid))

        return user_rowid

    def add_group(self, domain, name):
        domain = domain.split('.')[0].upper()

        self.conn.execute("SELECT * FROM groups WHERE LOWER(domain)=LOWER(?) AND LOWER(name)=LOWER(?)", [domain, name])
        results = self.conn.fetchall()

        if not len(results):
            self.conn.execute("INSERT INTO groups (domain, name) VALUES (?,?)", [domain, name])

        self.conn.close()

        logging.debug('add_group(domain={}, name={}) => {}'.format(domain, name, self.conn.lastrowid))

        return self.conn.lastrowid

    def remove_credentials(self, credIDs):
        """
        Removes a credential ID from the database
        """
        for credID in credIDs:

            self.conn.execute("DELETE FROM users WHERE id=?", [credID])
            self.conn.close()

    def add_admin_user(self, credtype, domain, username, password, host, userid=None):
        domain = domain.split('.')[0].upper()

        if userid:
            self.conn.execute("SELECT * FROM users WHERE id=?", [userid])
            users = self.conn.fetchall()
        else:
            self.conn.execute("SELECT * FROM users WHERE credtype=? AND LOWER(domain)=LOWER(?) AND LOWER(username)=LOWER(?) AND password=?", [credtype, domain, username, password])
            users = self.conn.fetchall()

        self.conn.execute('SELECT * FROM computers WHERE ip LIKE ?', [host])
        hosts = self.conn.fetchall()

        if len(users) and len(hosts):
            for user, host in zip(users, hosts):
                userid = user[0]
                hostid = host[0]

                #Check to see if we already added this link
                self.conn.execute("SELECT * FROM admin_relations WHERE userid=? AND computerid=?", [userid, hostid])
                links = self.conn.fetchall()

                if not len(links):
                    self.conn.execute("INSERT INTO admin_relations (userid, computerid) VALUES (?,?)", [userid, hostid])

        self.conn.close()

    def get_admin_relations(self, userID=None, hostID=None):
        if userID:
            self.conn.execute("SELECT * FROM admin_relations WHERE userid=?", [userID])

        elif hostID:
            self.conn.execute("SELECT * FROM admin_relations WHERE computerid=?", [hostID])

        else:
            self.conn.execute("SELECT * FROM admin_relations")

        results = self.conn.fetchall()
        self.conn.close()

        return results

    def get_group_relations(self, userID=None, groupID=None):
        if userID and groupID:
            self.conn.execute("SELECT * FROM group_relations WHERE userid=? and groupid=?", [userID, groupID])

        elif userID:
            self.conn.execute("SELECT * FROM group_relations WHERE userid=?", [userID])

        elif groupID:
            self.conn.execute("SELECT * FROM group_relations WHERE groupid=?", [groupID])

        results = self.conn.fetchall()
        self.conn.close()

        return results

    def remove_admin_relation(self, userIDs=None, hostIDs=None):
        if userIDs:
            for userID in userIDs:
                self.conn.execute("DELETE FROM admin_relations WHERE userid=?", [userID])

        elif hostIDs:
            for hostID in hostIDs:
                self.conn.execute("DELETE FROM admin_relations WHERE hostid=?", [hostID])

        self.conn.close()

    def remove_group_relations(self, userID=None, groupID=None):
        if userID:
            self.conn.execute("DELETE FROM group_relations WHERE userid=?", [userID])

        elif groupID:
            self.conn.execute("DELETE FROM group_relations WHERE groupid=?", [groupID])

        results = self.conn.fetchall()
        self.conn.close()

        return results

    def is_credential_valid(self, credentialID):
        """
        Check if this credential ID is valid.
        """
        self.conn.execute('SELECT * FROM users WHERE id=? AND password IS NOT NULL LIMIT 1', [credentialID])
        results = self.conn.fetchall()
        self.conn.close()
        return len(results) > 0

    def is_credential_local(self, credentialID):
        self.conn.execute('SELECT domain FROM users WHERE id=?', [credentialID])
        user_domain = self.conn.fetchall()

        if user_domain:
            self.conn.execute('SELECT * FROM computers WHERE LOWER(hostname)=LOWER(?)', [user_domain])
            results = self.conn.fetchall()
            self.conn.close()
            return len(results) > 0

    def get_credentials(self, filterTerm=None, credtype=None):
        """
        Return credentials from the database.
        """
        # if we're returning a single credential by ID
        if self.is_credential_valid(filterTerm):
            self.conn.execute("SELECT * FROM users WHERE id=?", [filterTerm])

        elif credtype:
            self.conn.execute("SELECT * FROM users WHERE credtype=?", [credtype])

        # if we're filtering by username
        elif filterTerm and filterTerm != '':
            self.conn.execute("SELECT * FROM users WHERE LOWER(username) LIKE LOWER(?)", ['%{}%'.format(filterTerm)])

        # otherwise return all credentials
        else:
            self.conn.execute("SELECT * FROM users")

        results = self.conn.fetchall()
        self.conn.close()
        return results

    def is_user_valid(self, userID):
        """
        Check if this User ID is valid.
        """
        self.conn.execute('SELECT * FROM users WHERE id=? LIMIT 1', [userID])
        results = self.conn.fetchall()
        self.conn.close()
        return len(results) > 0

    def get_users(self, filterTerm=None):
        if self.is_user_valid(filterTerm):
            self.conn.execute("SELECT * FROM users WHERE id=? LIMIT 1", [filterTerm])

        # if we're filtering by username
        elif filterTerm and filterTerm != '':
            self.conn.execute("SELECT * FROM users WHERE LOWER(username) LIKE LOWER(?)", ['%{}%'.format(filterTerm)])

        else:
            self.conn.execute("SELECT * FROM users")

        results = self.conn.fetchall()
        self.conn.close()
        return results

    def get_user(self, domain, username):
        self.conn.execute("SELECT * FROM users WHERE LOWER(domain)=LOWER(?) AND LOWER(username)=LOWER(?)", [domain, username])
        results = self.conn.fetchall()
        self.conn.close()
        return results

    def is_computer_valid(self, hostID):
        """
        Check if this host ID is valid.
        """
        self.conn.execute('SELECT * FROM computers WHERE id=? LIMIT 1', [hostID])
        results = self.conn.fetchall()
        self.conn.close()
        return len(results) > 0

    def get_computers(self, filterTerm=None, domain=None):
        """
        Return hosts from the database.
        """
        # if we're returning a single host by ID
        if self.is_computer_valid(filterTerm):
            self.conn.execute("SELECT * FROM computers WHERE id=? LIMIT 1", [filterTerm])

        # if we're filtering by domain controllers
        elif filterTerm == 'dc':
            if domain:
                self.conn.execute("SELECT * FROM computers WHERE dc=1 AND LOWER(domain)=LOWER(?)", [domain])
            else:
                self.conn.execute("SELECT * FROM computers WHERE dc=1")

        # if we're filtering by ip/hostname
        elif filterTerm and filterTerm != "":
            self.conn.execute("SELECT * FROM computers WHERE ip LIKE ? OR LOWER(hostname) LIKE LOWER(?)", ['%{}%'.format(filterTerm), '%{}%'.format(filterTerm)])

        # otherwise return all computers
        else:
            self.conn.execute("SELECT * FROM computers")

        results = self.conn.fetchall()
        self.conn.close()
        return results

    def get_domain_controllers(self, domain=None):
        return self.get_computers(filterTerm='dc', domain=domain)

    def is_group_valid(self, groupID):
        """
        Check if this group ID is valid.
        """
        self.conn.execute('SELECT * FROM groups WHERE id=? LIMIT 1', [groupID])
        results = self.conn.fetchall()
        self.conn.close()

        logging.debug('is_group_valid(groupID={}) => {}'.format(groupID, True if len(results) else False))
        return len(results) > 0

    def get_groups(self, filterTerm=None, groupName=None, groupDomain=None):
        """
        Return groups from the database
        """
        if groupDomain:
            groupDomain = groupDomain.split('.')[0].upper()

        if self.is_group_valid(filterTerm):
            self.conn.execute("SELECT * FROM groups WHERE id=? LIMIT 1", [filterTerm])

        elif groupName and groupDomain:
            self.conn.execute("SELECT * FROM groups WHERE LOWER(name)=LOWER(?) AND LOWER(domain)=LOWER(?)", [groupName, groupDomain])

        elif filterTerm and filterTerm !="":
            self.conn.execute("SELECT * FROM groups WHERE LOWER(name) LIKE LOWER(?)", ['%{}%'.format(filterTerm)])

        else:
            self.conn.execute("SELECT * FROM groups")

        results = self.conn.fetchall()
        self.conn.close()
        logging.debug('get_groups(filterTerm={}, groupName={}, groupDomain={}) => {}'.format(filterTerm, groupName, groupDomain, results))
        return results
